export interface Citation {
  call_id: string;
  patient_id: string;
  patient_name: string;
  date: string;
  turn_start: number;
  turn_end: number;
  quote: string;
}

export interface AskFilters {
  patient_id: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  answerable: boolean;
  confidence: string;
  citations: Citation[];
  retrieval_debug: {
    mode: string;
    candidate_count: number;
  };
  filters: AskFilters;
}

export interface TranscriptTurn {
  turn_number: number;
  speaker: string;
  text: string;
}

export interface TranscriptCall {
  call_id: string;
  date: string;
  patient: {
    id: string;
    name: string;
    age: number;
  };
  duration_seconds: number;
  turns: TranscriptTurn[];
}

export interface Patient {
  id: string;
  name: string;
  age: number;
}

export interface SafetyEvent {
  category: string;
  severity: string;
  call_id: string;
  turn_number: number;
  matched_text: string;
  explanation: string;
  classifier_type: string;
}
