import os
import uuid
import lancedb
import ollama
from datetime import datetime, timezone
from mirai.core.utils.assets_check import assets_check

class Memory:
    def __init__(self, session_id="default", system_prompt="你叫mirai，你是全世界最好的女朋友", storage_dir=None, max_recent=10):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_dir = storage_dir if storage_dir else os.path.join(base_dir, ".lancedb")
        
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.max_recent = max_recent
        self.embed_model = "qwen3-embedding:0.6b"

        assets_check()

        self.db = lancedb.connect(self.db_dir)
        self.table_name = "chat_history"
        self._init_table()

    def _init_table(self):
        if self.table_name not in self.db.table_names():
            return

        table = self.db.open_table(self.table_name)
        schema_fields = set(table.schema.names)
        required_fields = {
            "id",
            "vector",
            "session_id",
            "role",
            "content",
            "timestamp",
            "timestamp_num",
        }

        if required_fields.issubset(schema_fields):
            return

        self._migrate_table(table)

    def _migrate_table(self, table):
        rows = table.to_pandas().to_dict(orient="records")
        migrated_rows = []
        fallback_timestamp_num = int(datetime.now(timezone.utc).timestamp() * 1000)

        for index, row in enumerate(rows):
            content = row.get("content", "") or ""
            vector = row.get("vector")
            timestamp = row.get("timestamp") or self._format_timestamp()
            timestamp_num = self._parse_timestamp_num(
                row.get("timestamp_num"),
                timestamp,
                fallback_timestamp_num + index,
            )

            migrated_rows.append(
                {
                    "id": row.get("id") or str(uuid.uuid4()),
                    "vector": self._normalize_vector(vector, content),
                    "session_id": row.get("session_id") or self.session_id,
                    "role": row.get("role") or "user",
                    "content": content,
                    "timestamp": timestamp,
                    "timestamp_num": timestamp_num,
                }
            )

        self.db.drop_table(self.table_name, ignore_missing=True)
        if migrated_rows:
            self.db.create_table(self.table_name, data=migrated_rows)

    def _format_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")

    def _parse_timestamp_num(self, timestamp_num, timestamp, fallback):
        if timestamp_num is not None:
            return int(timestamp_num)

        try:
            parsed = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S %A")
            return int(parsed.replace(tzinfo=timezone.utc).timestamp() * 1000)
        except (TypeError, ValueError):
            return fallback

    def _normalize_vector(self, vector, content: str):
        if vector is None:
            return self._get_embedding(content)
        if hasattr(vector, "tolist"):
            return vector.tolist()
        return list(vector)

    def _get_embedding(self, text: str):
        try:
            response = ollama.embed(
                model=self.embed_model,
                input=text,
            )
            return response.embeddings[0]
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            return [0.0] * 1024

    def add_message(self, role: str, content: str):
        timestamp = self._format_timestamp()
        timestamp_num = int(datetime.now(timezone.utc).timestamp() * 1000)
        vector = self._get_embedding(content)
        message_id = str(uuid.uuid4())

        data = [{
            "id": message_id,
            "vector": vector,
            "session_id": self.session_id,
            "role": role,
            "content": content,
            "timestamp": timestamp,
            "timestamp_num": timestamp_num,
        }]

        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.add(data)
        else:
            self.db.create_table(self.table_name, data=data)

        return message_id

    def get_context(self):
        formatted_messages = [{"role": "system", "content": self.system_prompt}]
        
        if self.table_name not in self.db.table_names():
            return formatted_messages

        table = self.db.open_table(self.table_name)
        where_clause = f"session_id = '{self.session_id}'"
        total_messages = table.count_rows(where_clause)
        offset = max(total_messages - self.max_recent, 0)
        
        results = (
            table.search(
                query=None,
                ordering_field_name="timestamp_num"
            )
            .where(where_clause)
            .offset(offset)
            .limit(self.max_recent)
            .to_list()
        )

        for msg in results:
            if msg["role"] == "assistant":
                formatted_content = f"{msg['content']}"
                formatted_messages.append({"role": "assistant", "content": formatted_content})
            elif msg["role"] == "user":
                formatted_content = f"[{msg['timestamp']}] {msg['content']}"
                formatted_messages.append({"role": "user", "content": formatted_content})
            else:
                continue
        return formatted_messages

    def search_memory(self, query: str, limit: int = 5):
        if self.table_name not in self.db.table_names():
            return []
            
        query_vector = self._get_embedding(query)
        table = self.db.open_table(self.table_name)
        
        results = table.search(query_vector) \
            .where(f"session_id = '{self.session_id}'") \
            .limit(limit) \
            .to_list()
            
        return results

    def clear_history(self):
        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.delete(f"session_id = '{self.session_id}'")

    def delete_message(self, message_id: str):
        if self.table_name in self.db.table_names():
            table = self.db.open_table(self.table_name)
            table.delete(f"id = '{message_id}'")
