export interface Citation {
  call_id: string;
  patient_id: string;
  patient_name: string;
  date: string;
  turn_start: number;
  turn_end: number;
  quote: string;
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
