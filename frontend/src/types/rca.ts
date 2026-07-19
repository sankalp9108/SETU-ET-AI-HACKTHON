export interface RCAQueryRequest {
  equipment_id: string;
}

export interface RCATimelineEntry {
  event_type: string;
  date: string;
  description: string;
  source_document: string;
}

export interface RCAQueryResponse {
  equipment_id?: string;
  failure_summary?: string;
  contributing_factors?: string[];
  recommendation?: string;
  timeline?: RCATimelineEntry[];
  insufficient_data?: boolean;
  explanation?: string;
}
