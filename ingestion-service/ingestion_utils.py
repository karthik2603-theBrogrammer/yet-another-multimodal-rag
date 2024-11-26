from langchain_core.messages import HumanMessage

def image_captioning(llm, img_base64, prompt):
    ''' Image summary '''
    message = HumanMessage(
    content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
            },
        ]
    )
    ai_msg = llm.invoke([message])
    ai_msg.content
    print(ai_msg.content)
    return ai_msg.content