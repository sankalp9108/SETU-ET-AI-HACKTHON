export interface LessonsLearnedRequest {
  description: string;
}

export interface LessonsLearnedAlert {
  filename: string;
  similarity: number;
  excerpt: string;
  shared_equipment_ids: string[];
  note: string;
}

export interface LessonsLearnedReport {
  alerts: LessonsLearnedAlert[];
  insufficient_data: boolean;
  explanation?: string;
}
