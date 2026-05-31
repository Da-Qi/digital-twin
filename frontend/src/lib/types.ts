export interface Conversation {
  id: string;
  title: string | null;
  summary: string | null;
  message_count: number;
  token_count: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  token_count: number;
  correction_flag: boolean;
  created_at: string;
}

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  source_type: string;
  authorship: string;
  char_count: number;
  chunk_count: number;
  processing_status: "pending" | "processing" | "ready" | "failed";
  metadata?: { knowledge_status?: string; knowledge_extracted?: any };
  created_at: string;
}

export interface PersonalityProfile {
  id: string;
  version: number;
  status: string;
  summary: string | null;
  traits: PersonalityTrait[];
  created_at: string;
  activated_at: string | null;
}

export interface PersonalityTrait {
  id: string;
  category: string;
  trait_name: string;
  value: any;
  confidence: number;
  evidence_refs: string[] | null;
}

export interface Feedback {
  id: string;
  target_message_id: string;
  feedback_type: string;
  classification: string | null;
  user_input: string | null;
  created_at: string;
}
