export type PriorityLevel = "rojo" | "amarillo" | "verde";

export type MessageRole = "user" | "assistant" | "system";
export type MessageInputType = "texto" | "audio";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  input_type: MessageInputType;
  content: string;
  audio_url: string | null;
  created_at: string;
}

export interface ExecutedAction {
  type: string;
  entity_type: string;
  entity_id: string;
  title: string;
}

export interface ChatResponse {
  conversation_id: string;
  user_message: Message;
  assistant_message: Message;
  priority: PriorityLevel;
  needs_clarification: boolean;
  executed_actions: ExecutedAction[];
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: "pendiente" | "en_progreso" | "completada" | "cancelada";
  priority: PriorityLevel;
  due_date: string | null;
  project_id: string | null;
}

export interface EventItem {
  id: string;
  title: string;
  description: string | null;
  location: string | null;
  start_time: string;
  end_time: string | null;
  priority: PriorityLevel;
}

export interface Reminder {
  id: string;
  title: string;
  remind_at: string;
  status: "pendiente" | "enviado" | "completado" | "cancelado";
}

export interface Idea {
  id: string;
  title: string;
  content: string | null;
  priority: PriorityLevel;
}
