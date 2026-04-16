import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageSquare, Trash2, ExternalLink, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import api, { Conversation } from '../services/api';

export default function ConversationsPage() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setLoading(true);
    try {
      const data = await api.getConversations(20);
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    try {
      await api.deleteConversation(conversationId);
      setConversations(convs => convs.filter(c => c.id !== conversationId));
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation');
    }
  };

  const getConversationPreview = (conv: Conversation) => {
    const userMessages = conv.messages.filter(m => m.role === 'user');
    if (userMessages.length === 0) return 'New conversation';
    return userMessages[0].content.substring(0, 100) + (userMessages[0].content.length > 100 ? '...' : '');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Conversation History</h1>
        <p className="text-sm text-gray-600 mt-1">
          View and manage your past conversations
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <MessageSquare className="w-16 h-16 text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No conversations yet
            </h3>
            <p className="text-gray-600 mb-4">
              Start a new chat to begin asking questions
            </p>
            <button
              onClick={() => navigate('/chat')}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              Start Chatting
            </button>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto space-y-3">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className="bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-all p-4 hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-2">
                      <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <span className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(conv.created_at), { addSuffix: true })}
                      </span>
                      <span className="text-xs text-gray-300">•</span>
                      <span className="text-xs text-gray-500">
                        {conv.messages.length} messages
                      </span>
                    </div>
                    <p className="text-sm text-gray-900 mb-3">
                      {getConversationPreview(conv)}
                    </p>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => navigate(`/chat/${conv.id}`)}
                        className="flex items-center text-sm text-primary-600 hover:text-primary-700 font-medium"
                      >
                        <ExternalLink className="w-4 h-4 mr-1" />
                        Continue
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteConversation(conv.id)}
                    className="text-gray-400 hover:text-red-600 transition-colors ml-4"
                    title="Delete conversation"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}