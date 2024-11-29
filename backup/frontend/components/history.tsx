import React, { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  MessageSquare,
  MoreHorizontal,
  Plus,
  Edit,
  Share2,
  Trash2
} from 'lucide-react';
import { useAuth } from "@/app/authProvider";
import { useConversationContext } from "@/app/ConversationContext";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

const MAX_SUMMARY_LENGTH = 30;

const HistoryComponent: React.FC = () => {
  const { isAuthenticated, axiosInstance } = useAuth();
  const router = useRouter();
  const { conversationList, setConversationList, currentConversationId, setCurrentConversationId } = useConversationContext();

  const [isEditing, setIsEditing] = useState<string | null>(null);
  const [editedSummaries, setEditedSummaries] = useState<{ [key: string]: string }>({});

  const fetchConversations = async () => {
    if (!isAuthenticated) return;

    try {
      const response = await axiosInstance.get('/api/newwww');

      // Assuming the API returns conversations categorized by date
      setConversationList(response.data.conversations);
      console.log(response.data)
    } catch (error: any) {
      toast.error(`Failed to fetch conversations: ${error.message}`);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [isAuthenticated]);

  const handleNewChat = async () => {
    try {
      const response = await axiosInstance.post('/api/conversation/create');
      const newConversationId = response.data.conversation_id;
      router.push(`/chat?conversation_id=${newConversationId}`);

      // Refresh conversation list
      console.log("is this being called ?")
      fetchConversations();
    } catch (error: any) {
      toast.error(`Failed to create new chat: ${error.message}`);
    }
  };

  const handleEditSummary = async (conversationId: string) => {
    try {
      await axiosInstance.patch(`/api/conversations/summary/edit`, {
        conversation_id: conversationId,
        summary: editedSummaries[conversationId],

      });

      // Reset editing state and refresh conversations
      setIsEditing(null);
      fetchConversations();
    } catch (error: any) {
      toast.error(`Failed to update summary: ${error.message}`);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    const confirmed = window.confirm('Are you sure you want to delete this conversation?');

    if (!confirmed) return;

    try {
      await axiosInstance.delete(`/api/conversations/${conversationId}/delete`);

      // Refresh conversation list 
      fetchConversations();

      // If currently viewed conversation was deleted, redirect to chat
      router.push('/chat');
    } catch (error: any) {
      toast.error(`Failed to delete conversation: ${error.message}`);
    }
  };

  const handleShareConversation = async (conversationId: string) => {
    try {
      const response = await axiosInstance.post(`/api/conversations/${conversationId}/share`);

      const shareLink = `${window.location.origin}/share/${conversationId}`;

      // Copy to clipboard and show toast
      navigator.clipboard.writeText(shareLink);
      toast.success('Conversation link copied to clipboard!');
    } catch (error: any) {
      toast.error(`Failed to share conversation: ${error.message}`);
    }
  };

  const renderConversationCategories = () => {
    const categories: Array<keyof typeof conversationList> = [
      'today', 'yesterday', 'last7Days', 'beforeThat'
    ];

    return categories.map(category => {
      const conversations = conversationList[category];

      if (conversations.length === 0) return null;

      return (
        <div key={category} className="mb-4">
          <h3 className="text-sm font-semibold text-muted-foreground mb-2 capitalize">
            {category.replace(/([A-Z])/g, ' $1').toLowerCase()}
          </h3>
          {conversations.map(conversation => (
            <ConversationItem
              key={conversation._id}
              conversation={conversation}
              isEditing={isEditing === conversation._id}
              editedSummary={editedSummaries[conversation._id] || conversation.summary}
              onEditStart={() => {
                setIsEditing(conversation._id);
                setEditedSummaries(prev => ({
                  ...prev,
                  [conversation._id]: conversation.summary
                }));
              }}
              onEditChange={(value) =>
                setEditedSummaries(prev => ({
                  ...prev,
                  [conversation._id]: value
                }))
              }
              onEditSubmit={() => handleEditSummary(conversation._id)}
              onDelete={() => handleDeleteConversation(conversation._id)}
              onShare={() => handleShareConversation(conversation._id)}
              onSelect={() => {
                setCurrentConversationId(conversation._id)
                router.push(`/chat?conversation_id=${conversation._id}`)
              }}
            />
          ))}
        </div>
      );
    });
  };

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col h-full justify-center items-center text-muted-foreground">
        <p>Please sign in to view your conversation history</p>
        <Button className="mt-4" onClick={() => router.push('/signin')}>
          Sign In
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <Button
        variant="outline"
        className="m-4 flex items-center"
        onClick={handleNewChat}
      >
        <Plus className="mr-2 h-4 w-4" /> New Chat
      </Button>

      <ScrollArea className="flex-1 px-4">
        {renderConversationCategories()}
      </ScrollArea>
    </div>
  );
};

interface ConversationItemProps {
  conversation: Conversation;
  isEditing: boolean;
  editedSummary: string;
  onEditStart: () => void;
  onEditChange: (value: string) => void;
  onEditSubmit: () => void;
  onDelete: () => void;
  onShare: () => void;
  onSelect: () => void;
}

const ConversationItem: React.FC<ConversationItemProps> = ({
  conversation,
  isEditing,
  editedSummary,
  onEditStart,
  onEditChange,
  onEditSubmit,
  onDelete,
  onShare,
  onSelect
}) => {
  const truncateSummary = (summary: string) =>
    summary.length > MAX_SUMMARY_LENGTH
      ? `${summary.substring(0, MAX_SUMMARY_LENGTH)}...`
      : summary;

  return (
    <div className="flex items-center justify-between hover:bg-accent rounded-md p-2 group">
      <div
        className="flex items-center space-x-3 flex-grow cursor-pointer"
        onClick={onSelect}
      >
        <MessageSquare className="h-5 w-5 text-muted-foreground" />

        {isEditing ? (
          <Input
            value={editedSummary}
            onChange={(e) => onEditChange(e.target.value)}
            onBlur={onEditSubmit}
            onKeyDown={(e) => e.key === 'Enter' && onEditSubmit()}
            className="flex-grow"
            autoFocus
          />
        ) : (
          <span className="truncate flex-grow">
            {truncateSummary(conversation.summary)}
          </span>
        )}
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="ml-2">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onEditStart}>
            <Edit className="mr-2 h-4 w-4" /> Edit
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onShare}>
            <Share2 className="mr-2 h-4 w-4" /> Share
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onDelete} className="text-destructive">
            <Trash2 className="mr-2 h-4 w-4" /> Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
};

export default function History() {
  return (
    <React.Suspense fallback={<div>Loading...</div>}>
      <HistoryComponent />
    </React.Suspense>
  );
}