from openai import OpenAI
import time
import streamlit as st
import requests
from dotenv import load_dotenv
import os


load_dotenv()

DID_API_ENV = os.getenv("DID_API")

def generate_video(script):
    url = "https://api.d-id.com/talks"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization" : DID_API_ENV
        }

    payload = {
        "script": {
            "type": "text",
            "subtitles": "false",
            "provider": {
                "type": "microsoft",
                "voice_id": "en-US-JennyNeural"
            },
            "ssml": "false",
            "input":script
        },
        "config": {
            "fluent": "false",
            "pad_audio": "0.0",
            "stitch": "true"
        },
        "source_url": "https://photosfordidd.s3.eu-central-1.amazonaws.com/alice.png"
    }

    try:
        print(f"ATTEMPTING TO GENERATE VIDEO WITH SCRIPT: {script}")
        print(f"URL: {url}")
        print(f"PAYLOAD: {payload}")
        print(f"HEADERS: {headers}")

        response = requests.post(url, json=payload, headers=headers)
        print(f"RESPONSE: {response}")

        if response.status_code == 201:
            print("RESPONSE WAS 201")
            res = response.json()
            id = res["id"]
            status = "created"
            while status != "done":
                print("TRYING AGAIN")
                try:
                    getresponse = requests.get(f"{url}/{id}", headers=headers)
                except Exception as e:
                    print(f"EXCEPTION: {e}")
                    time.sleep(10)
                    getresponse = requests.get(f"{url}/{id}", headers=headers)
                print(f"GET RESPONSE: {getresponse}")
                if getresponse.status_code == 200:
                    status = res["status"]
                    res = getresponse.json()
                    print(f"RESPONSE: {res}")
                    if res["status"] == "done":
                        print("ITS DONE")
                        video_url =  res["result_url"]
                    else:
                        print("WILL TRY AGAIN IN 10 SECONDS")
                        time.sleep(3)
                else:
                    status = "error"
                    video_url = "error"
        else:
            print("RESPONSE WAS NOT 201")
            video_url = "error"   
    except Exception as e:
        print(f"EXCEPTION: {e}")      
        video_url = "error"          

    return video_url 
    avatarlist = {
        "Male": "https://photosfordidd.s3.eu-central-1.amazonaws.com/alice.png",
        "Female": "https://photosfordidd.s3.eu-central-1.amazonaws.com/alice.png"
    }

# with while loop continuously check the status of a run until it neither 'queued' nor 'in progress'
def wait_for_complete(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = st.session_state.client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

def process_conversation(conversation):
    citations = []

    full_response = None
    print(f"CONVERSATION: {conversation}")

    # Iterate over all replies
    for c in conversation:
        print(f"REPLY: {c}")
        if c.role == "assistant":
            message_content = c.content[0].text
            print(f"MESSAGE CONTENT: {message_content}")
            annotations = message_content.annotations
            print(f"ANNOTATIONS: {annotations}")

            # Iterate over the annotations and add footnotes
            for index, annotation in enumerate(annotations):
                # Replace the text with a footnote
                print(f"ANNOTATION: {annotation}")
                message_content.value = message_content.value.replace(
                    annotation.text, f" [{index}]"
                )

                # Gather citations based on annotation attributes
                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = st.session_state.client.files.retrieve(
                        file_citation.file_id
                    )
                    citations.append(
                        f"[{index}] {file_citation.quote} from {cited_file.filename}"
                    )
                elif file_path := getattr(annotation, "file_path", None):
                    cited_file = st.session_state.client.files.retrieve(
                        file_path.file_id
                    )
                    citations.append(
                        f"[{index}] Click <here> to download {cited_file.filename}"
                    )

            # Combine message content and citations
            print(f"MESSAGE CONTENT RIGHT AT THE END: {message_content}")
            full_response = message_content.value + "\n" + "\n".join(citations)
            print(f"FULL RESPONSE RIGHT AT THE END: {full_response}")


    return full_response

def main():
    api_key = st.secrets["OPENAI_API_KEY"]
    assistant_id = st.secrets["ASSISTANT_ID"]
    video_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/baselinevideo2.mp4"   
    image2_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/2.png"
    image3_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/PDFcover.png"
    image4_path = "https://photosfordidd.s3.eu-central-1.amazonaws.com/SC.png"
    
    st.set_page_config(
        page_title="Cigna AI Assistant",
        page_icon="📚",
        layout="wide"
    ) 
       
    st.sidebar.write(f'<video width="480" height="360" controls autoplay><source src="{video_path}" type="video/mp4"></video>', unsafe_allow_html=True)  
    st.sidebar.image(image2_path, caption='',width=300)
    
    col1,col2 = st.columns(2)       
        
    with col1:                    
         image_path = "https://logos-world.net/wp-content/uploads/2022/05/Cigna-Logo.png"
         st.image(image_path, caption='',width=300)    

    with col2:
        with st.expander("About",expanded=True):             
                st.header("I am trained on the below collaterals")
                st.image(image3_path, caption='https://photosfordidd.s3.eu-central-1.amazonaws.com/Cigna+Healthguard+Brochure.pdf',width=640)
                st.image(image4_path, caption='',width=640)
               
    

    add_selectbox = st.sidebar.selectbox(
        'How often would you like to be contacted?',
        ('Daily', 'Weekly', 'Monthly','Never')
    )
    
    add_selectbox = st.sidebar.selectbox(
        'How would you like to be contacted?',
        ('Email', 'WhatsApp', 'Phone')
    )
    
    slider_value = st.sidebar.slider("How satisfied out of 10 were you with your last Cigna interaction?", 0, 5, 10)

    # Initiate st.session_state
    st.session_state.client = OpenAI(api_key=api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "start_chat" not in st.session_state:
        st.session_state.start_chat = False

    if st.session_state.client:
        st.session_state.start_chat = True

    if "processed_response" not in st.session_state:
                st.session_state.sprocessed_response = []
                 
    if st.session_state.start_chat:
        # Display existing messages in the chat
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                with col1:
                    st.markdown(message["content"])

                # Accept user input
                
    with col1:        
        if prompt := st.chat_input("Hello how can I help?"):
            print("---------------------PROMPT RECEIVED-------------------")
            print(f"PROMPT: {prompt}")
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            print(f"MESSAGES: {st.session_state.messages}")
            # Display user message in chat message container
            with col1:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # Create a thread
            st.session_state.thread = st.session_state.client.beta.threads.create()

            # Add a Message to the thread
            st.session_state.client.beta.threads.messages.create(
                thread_id=st.session_state.thread.id,
                role="user",
                content=prompt,
            )

            # As of now, assistant and thread are not associated to eash other
            # You need to create a run in order to tell the assistant at which thread to look at
            run = st.session_state.client.beta.threads.runs.create(
                thread_id=st.session_state.thread.id,
                assistant_id=assistant_id,
            )    

            run = wait_for_complete(run, st.session_state.thread)

            # once the run has completed, list the messages in the thread -> they are ordered in reverse chronological order
            conversation = st.session_state.client.beta.threads.messages.list(
                thread_id=st.session_state.thread.id
            )
            print(f"REPLIES: {conversation}")

            # Add the processed response to session state          
            processed_response = process_conversation(conversation) 
            print(f"PROCESSED_RESPONSE: {processed_response}")

            st.session_state.messages.append(
                    {"role": "assistant", "content": processed_response}
                )    
            print(f"MESSAGES: {st.session_state.messages}")       
                                                              
            video_url = generate_video(processed_response[:25])
            with col1:
             st.write(f'<video width="640" height="480" controls autoplay><source src="{video_url}" type="video/mp4"></video>', unsafe_allow_html=True)
  
             with st.chat_message("assistant"):
                  st.markdown(processed_response)
                 
if __name__ == "__main__":
    main()