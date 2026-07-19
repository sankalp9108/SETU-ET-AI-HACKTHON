export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface ComplianceGap {
  document_filename: string;
  severity: Severity;
  description: string;
  evidence: string;
  regulation_reference: string | null;
}

export interface ComplianceReport {
  gaps: ComplianceGap[];
  insufficient_data: boolean;
  documents_checked: number;
  regulatory_documents_used: number;
  explanation?: string;
}
