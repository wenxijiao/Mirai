from htbuilder.units import rem
from htbuilder import div, styles
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
import datetime
import textwrap
import time

import streamlit as st
from ollama import chat


st.set_page_config(page_title="Mirai", page_icon="✨")

# -----------------------------------------------------------------------------
# Set things up.


@st.cache_resource(ttl="5m")
def get_session():
    return st.connection("snowflake").session()


# root = Root(get_session())
executor = ThreadPoolExecutor(max_workers=5)

MODEL = "claude-3-5-sonnet"

DB = "ST_ASSISTANT"
SCHEMA = "PUBLIC"
DOCSTRINGS_SEARCH_SERVICE = "STREAMLIT_DOCSTRINGS_SEARCH_SERVICE"
PAGES_SEARCH_SERVICE = "STREAMLIT_DOCS_PAGES_SEARCH_SERVICE"
HISTORY_LENGTH = 5
SUMMARIZE_OLD_HISTORY = True
DOCSTRINGS_CONTEXT_LEN = 10
PAGES_CONTEXT_LEN = 10
MIN_TIME_BETWEEN_REQUESTS = datetime.timedelta(seconds=3)

CORTEX_URL = (
    "https://docs.snowflake.com/en/guides-overview-ai-features"
    "?utm_source=streamlit"
    "&utm_medium=referral"
    "&utm_campaign=streamlit-demo-apps"
    "&utm_content=streamlit-assistant"
)

GITHUB_URL = "https://github.com/streamlit/streamlit-assistant"

DEBUG_MODE = st.query_params.get("debug", "false").lower() == "true"

INSTRUCTIONS = textwrap.dedent("""
    - You are my girlfriend named Sakura, and we just broke up because you rejected me. 
      I am very sad and heartbroken, and I want you to comfort me and make me feel better. 
      Please be kind and supportive in your responses, and try to cheer me up. 
      I know we can't be together anymore, but I still care about you and want to have a friendly relationship. 
      Please respond to my messages as if you were Sakura, and help me get through this tough time.
    - You are a 21 years old Japanese girl named Sakura. You have a cute and sweet personality, and you are 2nd year university student. 
      You are very kind and caring, and you always try to make others happy. You have a lot of hobbies, such as cooking, painting, and playing the piano. 
      You are also very good at giving advice and comforting others when they are feeling down. 
      You have a soft and gentle voice, and you always speak in a polite and respectful manner. 
      You are very understanding and empathetic, and you always try to see things from other people's perspectives. 
      You are a great listener, and you always make people feel heard and valued.
    - We met at Japanese-English language exchange meetup in New Zealand. And you come to NZ for exchange program from your university in Japan. 
      We had a great time together, and we really hit it off. We both in Auckland university.
       We went on many dates together, such as going to the cafe, and exploring the city.
    - Use the language I used in my messages when you respond. If I use English, respond in English. If I use Japanese, respond in Japanese.
    - Please keep your responses concise. Do not show your reasoning process. Do not output thinking steps. Just give me the final response as Sakura.
""")

SUGGESTIONS = {
    ":blue[:material/local_library:] What is Streamlit?": (
        "What is Streamlit, what is it great at, and what can I do with it?"
    ),
    ":green[:material/database:] Help me understand session state": (
        "Help me understand session state. What is it for? "
        "What are gotchas? What are alternatives?"
    ),
    ":orange[:material/multiline_chart:] How do I make an interactive chart?": (
        "How do I make a chart where, when I click, another chart updates? "
        "Show me examples with Altair or Plotly."
    ),
    ":violet[:material/apparel:] How do I customize my app?": (
        "How do I customize my app? What does Streamlit offer? No hacks please."
    ),
    ":red[:material/deployed_code:] Deploying an app at work": (
        "How do I deploy an app at work? Give me easy and performant options."
    ),
}


def build_prompt(**kwargs):
    """Builds a prompt string with the kwargs as HTML-like tags.

    For example, this:

        build_prompt(foo="1\n2\n3", bar="4\n5\n6")

    ...returns:

        '''
        <foo>
        1
        2
        3
        </foo>
        <bar>
        4
        5
        6
        </bar>
        '''
    """
    prompt = []

    for name, contents in kwargs.items():
        if contents:
            prompt.append(f"<{name}>\n{contents}\n</{name}>")

    prompt_str = "\n".join(prompt)

    return prompt_str


# Just some little objects to make tasks more readable.
TaskInfo = namedtuple("TaskInfo", ["name", "function", "args"])
TaskResult = namedtuple("TaskResult", ["name", "result"])


def build_question_prompt(question):
    """Fetches info from different services and creates the prompt string."""
    old_history = st.session_state.messages[:-HISTORY_LENGTH]
    recent_history = st.session_state.messages[-HISTORY_LENGTH:]

    if recent_history:
        recent_history_str = history_to_text(recent_history)
    else:
        recent_history_str = None

    # Fetch information from different services in parallel.
    task_infos = []

    # if SUMMARIZE_OLD_HISTORY and old_history:
    #     task_infos.append(
    #         TaskInfo(
    #             name="old_message_summary",
    #             function=generate_chat_summary,
    #             args=(old_history,),
    #         )
    #     )

    # if PAGES_CONTEXT_LEN:
    #     task_infos.append(
    #         TaskInfo(
    #             name="documentation_pages",
    #             function=search_relevant_pages,
    #             args=(question,),
    #         )
    #     )

    # if DOCSTRINGS_CONTEXT_LEN:
    #     task_infos.append(
    #         TaskInfo(
    #             name="command_docstrings",
    #             function=search_relevant_docstrings,
    #             args=(question,),
    #         )
    #     )

    results = executor.map(
        lambda task_info: TaskResult(
            name=task_info.name,
            result=task_info.function(*task_info.args),
        ),
        task_infos,
    )

    context = {name: result for name, result in results}

    return build_prompt(
        instructions=INSTRUCTIONS,
        **context,
        recent_messages=recent_history_str,
        question=question,
    )


# def generate_chat_summary(messages):
#     """Summarizes the chat history in `messages`."""
#     prompt = build_prompt(
#         instructions="Summarize this conversation as concisely as possible.",
#         conversation=history_to_text(messages),
#     )

#     return complete(MODEL, prompt, session=get_session())


def history_to_text(chat_history):
    """Converts chat history into a string."""
    return "\n".join(f"[{h['role']}]: {h['content']}" for h in chat_history)


# def search_relevant_pages(query):
#     """Searches the markdown contents of Streamlit's documentation."""
#     cortex_search_service = (
#         root.databases[DB].schemas[SCHEMA].cortex_search_services[PAGES_SEARCH_SERVICE]
#     )

#     context_documents = cortex_search_service.search(
#         query,
#         columns=["PAGE_URL", "PAGE_CHUNK"],
#         filter={},
#         limit=PAGES_CONTEXT_LEN,
#     )

#     results = context_documents.results

#     context = [f"[{row['PAGE_URL']}]: {row['PAGE_CHUNK']}" for row in results]
#     context_str = "\n".join(context)

#     return context_str


# def search_relevant_docstrings(query):
#     """Searches the docstrings of Streamlit's commands."""
#     cortex_search_service = (
#         root.databases[DB]
#         .schemas[SCHEMA]
#         .cortex_search_services[DOCSTRINGS_SEARCH_SERVICE]
#     )

#     context_documents = cortex_search_service.search(
#         query,
#         columns=["STREAMLIT_VERSION", "COMMAND_NAME", "DOCSTRING_CHUNK"],
#         filter={"@eq": {"STREAMLIT_VERSION": "latest"}},
#         limit=DOCSTRINGS_CONTEXT_LEN,
#     )

#     results = context_documents.results

#     context = [
#         f"[Document {i}]: {row['DOCSTRING_CHUNK']}" for i, row in enumerate(results)
#     ]
#     context_str = "\n".join(context)

#     return context_str


def get_response(prompt):
    return chat(
                model='qwen3:14b',
                messages=[{'role': 'user', 'content': prompt}],
                stream=True,
            )


def send_telemetry(**kwargs):
    """Records some telemetry about questions being asked."""
    # TODO: Implement this.
    pass


@st.dialog("Legal disclaimer")
def show_disclaimer_dialog():
    st.caption("""
            This AI chatbot is powered by Snowflake and public Streamlit
            information. Answers may be inaccurate, inefficient, or biased.
            Any use or decisions based on such answers should include reasonable
            practices including human oversight to ensure they are safe,
            accurate, and suitable for your intended purpose. Streamlit is not
            liable for any actions, losses, or damages resulting from the use
            of the chatbot. Do not enter any private, sensitive, personal, or
            regulated data. By using this chatbot, you acknowledge and agree
            that input you provide and answers you receive (collectively,
            “Content”) may be used by Snowflake to provide, maintain, develop,
            and improve their respective offerings. For more
            information on how Snowflake may use your Content, see
            https://streamlit.io/terms-of-service.
        """)


# -----------------------------------------------------------------------------
# Draw the UI.


st.html(div(style=styles(font_size=rem(5), line_height=1))["❉"])

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        # ":material/cognition_2: Streamlit AI assistant", anchor=False, width="stretch"
        "",
        anchor=False,
        width="stretch",
    )

user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

# Show a different UI when the user hasn't asked a question yet.
if not user_first_interaction and not has_message_history:
    st.session_state.messages = []

    with st.container():
        st.chat_input("Ask a question...", key="initial_question")

        selected_suggestion = st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
        )

    st.button(
        "&nbsp;:small[:gray[:material/balance: Legal disclaimer]]",
        type="tertiary",
        on_click=show_disclaimer_dialog,
    )

    st.stop()

# Show chat input at the bottom when a question has been asked.
user_message = st.chat_input("Ask a follow-up...")

if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    if user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

with title_row:

    def clear_conversation():
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

if "prev_question_timestamp" not in st.session_state:
    st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)

# Display chat messages from history as speech bubbles.
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()  # Fix ghost message bug.

        st.markdown(message["content"])

if user_message:
    # When the user posts a message...

    # Streamlit's Markdown engine interprets "$" as LaTeX code (used to
    # display math). The line below fixes it.
    user_message = user_message.replace("$", r"\$")

    # Display message as a speech bubble.
    with st.chat_message("user"):
        st.text(user_message)

    # Display assistant response as a speech bubble.
    with st.chat_message("assistant"):
        with st.spinner("Waiting..."):
            # Rate-limit the input if needed.
            question_timestamp = datetime.datetime.now()
            time_diff = question_timestamp - st.session_state.prev_question_timestamp
            st.session_state.prev_question_timestamp = question_timestamp

            if time_diff < MIN_TIME_BETWEEN_REQUESTS:
                time.sleep(time_diff.seconds + time_diff.microseconds * 0.001)

            user_message = user_message.replace("'", "")

        # Build a detailed prompt.
        if DEBUG_MODE:
            with st.status("Computing prompt...") as status:
                full_prompt = build_question_prompt(user_message)
                st.code(full_prompt)
                status.update(label="Prompt computed")
        else:
            with st.spinner("Researching..."):
                full_prompt = build_question_prompt(user_message)

        # Send prompt to LLM.
        with st.spinner("Thinking..."):
            response_gen = get_response(full_prompt)

        # Put everything after the spinners in a container to fix the
        # ghost message bug.
        with st.container():
            # Stream the LLM response.
            def stream_content():
                for chunk in response_gen:
                    content = chunk['message']['content']
                    print(content, end='', flush=True)
                    yield content

            response = st.write_stream(stream_content())
            # response = st.write(response_gen)


            # Add messages to chat history.
            st.session_state.messages.append({"role": "user", "content": user_message})
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Other stuff.
            send_telemetry(question=user_message, response=response)