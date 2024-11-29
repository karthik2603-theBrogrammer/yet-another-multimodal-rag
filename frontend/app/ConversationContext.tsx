'use client'

import React, { useContext, createContext, useState, useEffect } from "react"

interface Message {
    _id: string
    role: string
    content: string
    created_at: string
}
// a conversation can be a list of messages. message can be 
// by either the 'user' or the 'ai' itself.

interface Conversation {
    _id: string
    summary: string
    created_at?: string
    updated_at?: string
    messages: Message[]
}

interface ConversationByDate {
    today: Conversation[]
    yesterday: Conversation[]
    last7Days: Conversation[]
    beforeThat: Conversation[]
}

interface ConversationContextProps {
    conversationList: ConversationByDate
    setConversationList: React.Dispatch<React.SetStateAction<ConversationByDate>>
    isSidebarOpen: boolean
    setIsSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>
    currentConversationId: string
    setCurrentConversationId: React.Dispatch<React.SetStateAction<string>>
}

const ConversationContext = createContext<ConversationContextProps | undefined>(undefined)

export const useConversationContext = () => {
    const context = useContext(ConversationContext)
    if (context === undefined) {
        throw new Error(
            'useConversationContext must be used within a ConversationProvider'
        );
    }
    return context
}

interface ConversationContextProviderProps {
    children: React.ReactNode
}

export const ConversationProvider: React.FC<ConversationContextProviderProps> = ({ children }) => {
    const [conversationList, setConversationList] = useState<ConversationByDate>({
        today: [],
        yesterday: [],
        last7Days: [],
        beforeThat: []
    })
    const [currentConversationId, setCurrentConversationId] = useState<string>("")

    const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
    return (
        <ConversationContext.Provider
            value={{
                conversationList, setConversationList, isSidebarOpen, setIsSidebarOpen, currentConversationId, setCurrentConversationId
            }}
        >
            {children}
        </ConversationContext.Provider>
    )
}