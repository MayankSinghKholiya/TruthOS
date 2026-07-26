import { ChatView } from "@/components/chat/ChatView";

export default async function ExistingChatPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ChatView sessionId={sessionId} />;
}
