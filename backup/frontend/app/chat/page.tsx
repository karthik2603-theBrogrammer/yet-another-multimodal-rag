"use client"

import { useCallback, useEffect, useState } from 'react';
import { useChat } from 'ai/react';
import { ChatInput, ChatMessages } from '@/components/ui/chat';
import { useClientConfig } from '@/components/ui/chat/hooks/use-config';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useConversationContext } from '@/app/ConversationContext';
import { useAuth } from '@/app/authProvider';
import Loading from '@/components/loading';
import { toast } from 'sonner';


import axios from 'axios';

function ChatContentUI() {
    const { accessToken } = useAuth();
    const MESSAGES_API = "http://localhost:8080/api/newwww"
    const LLM_API = "http://localhost:8080/api/generate"
    const searchParams = useSearchParams();
    const router = useRouter();
    const { conversationList, setConversationList, currentConversationId, setCurrentConversationId } = useConversationContext();
    const [isClient, setIsClient] = useState(false);
    // const [currentConversationId, setCurrentConversationId] = useState<string>("")

    const fetchCurrentConversationId = (): string => {
        const page_conversation_id = searchParams.get("conversation_id")
        return page_conversation_id || ""
    }
    useEffect(() => {
        const page_conversation_id = fetchCurrentConversationId();
        if (!page_conversation_id) {
          router.back();
          return;
        }
    
        // Fetch the messages for the current conversation ID
        const fetchMessages = async () => {
          try {
            const response = await axios.get(MESSAGES_API, {
              headers: {
                Authorization: `Bearer ${accessToken}`,
              },
            });
    
            const conversation = response.data.conversations.today.find(
              (conv: any) => conv._id === page_conversation_id
            );
    
            if (conversation) {
              // Format the messages based on the response structure
              const formattedMessages = conversation.messages.map((msg: any) => ({
                id: msg._id,
                content: msg.content,
                role: msg.role === "user" ? "user" : "assistant", // Map 'human' to 'user' and 'assistant' stays the same
                createdAt: new Date(msg.created_at),
              }));
              setMessages(formattedMessages);
            }
          } catch (error) {
            toast("Error fetching conversation messages");
          }
        };
    
        fetchMessages();
      }, [searchParams, accessToken, router]);
    
    const { 
        messages,
        input,
        isLoading,
        handleSubmit,
        handleInputChange,
        reload,
        stop,
        append,
        setInput,
        setMessages,
    } = useChat({
        api: 'http://localhost:8080/api/generate/stream',
        streamProtocol: 'text',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
        },
        body: {
            conversation_id: fetchCurrentConversationId()
        },
        credentials: 'same-origin',
        onError: (error: unknown) => {
            if (!(error instanceof Error)) throw error;
            let errorMessage = 'An unexpected error occurred.';

            try {
                const errorResponse = JSON.parse(error.message);
                if(errorResponse['detail'] == "404: Chat session not found"){
                    toast(`Chat ${fetchCurrentConversationId()} has not been found. Please create a new chat and continue`)
                    return
                }
                if (errorResponse.detail === 'Not authenticated') {
                    alert('Session has expired. Please login again.');
                    router.push('/signin');
                    return;
                }

                if (errorResponse.detail) {
                    errorMessage = `Error: ${errorResponse.detail}`;
                } else if (errorResponse.errors) {
                    errorMessage = `Validation Errors: ${errorResponse.errors.join(
                        ', '
                    )}`;
                } else if (errorResponse.message) {
                    errorMessage = `Message: ${errorResponse.message}`;
                } else if (errorResponse.error) {
                    errorMessage = `Error: ${errorResponse.error}`;
                } else {
                    errorMessage = `Unknown error format: ${error.message}`;
                }
            } catch (parseError) {
                errorMessage = `Error parsing response: ${error.message}`;
            }

            toast(errorMessage);
        },
        onFinish: (message, { usage, finishReason }) => {
            console.log('Finished streaming message:', message);
            console.log('Token usage:', usage);
            console.log('Finish reason:', finishReason);
            console.log("All messages: ", messages)
        },
        onResponse: response => {
            console.log('Received HTTP response from server:', response);
        },
    });

    const updateMessageContent = (
        id: string,
        oldContent: string,
        newContent: string
    ) => {
        const messageIndex = messages.findIndex(
            (m: any) => m.role === 'user' && m.content === oldContent
        );
        if (messageIndex !== -1) {
            const updatedMessages = [...messages.slice(0, messageIndex)];
            setMessages(updatedMessages);

            append!({
                role: 'user',
                content: newContent,
            });
        }
    };


    return (
        <div className="w-full h-full flex justify-center items-center bg-primary-foreground">
            <div className="space-y-2 w-full  md:w-[90%] lg:w-[70%] h-full flex flex-col p-4">
                <Suspense fallback={<Loading />}>
                    <ChatMessages
                        messages={messages}
                        isLoading={isLoading}
                        reload={reload}
                        stop={stop}
                        append={append}
                        updateMessageContent={updateMessageContent}
                    />
                </Suspense>
                <Suspense fallback={<Loading />}>
                    <ChatInput
                        input={input}
                        handleSubmit={handleSubmit}
                        handleInputChange={handleInputChange}
                        isLoading={isLoading}
                        messages={messages}
                        append={append}
                        setInput={setInput}
                    />
                </Suspense>

            </div>
        </div>
    );
}

export default function Chat() {
    return (
        <Suspense fallback={<Loading />} >
            <ChatContentUI />
        </Suspense>
    )
}