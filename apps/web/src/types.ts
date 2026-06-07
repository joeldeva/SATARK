export type Role = 'admin' | 'sdrd' | 'fod' | 'dpd' | 'scd';
export type Language = 'en' | 'hi' | 'ta';
export type TrustLevel = 'Green' | 'Amber' | 'Red';
export type StatusLevel = 'pass' | 'warn' | 'fail';
export type QuestionType = 'text' | 'number' | 'choice' | 'adaptive' | 'date' | 'multi';

export interface User {
  username: string;
  password: string;
  role: Role;
  name: string;
}

export interface Enumerator {
  id: string;
  name: string;
  region: string;
  assigned: number;
  completed: number;
  trustScore: number;
  trustLevel: TrustLevel;
  trustTrend: number[];
}

export interface Household {
  id: string;
  prepop: {
    name: string;
    state: string;
    district: string;
  };
}

export interface SurveyQuestion {
  id: string;
  type: QuestionType;
  prepop?: boolean;
  codeType?: string | null;
  options?: string[];
  q?: Partial<Record<Language, string>>;
  rules?: {
    range?: [number, number];
    crossField?: {
      ifOccupation: string;
      max: number;
    };
    contextRef?: string;
  };
}

export interface BranchQuestion {
  id: string;
  q: Partial<Record<Language, string>>;
  options?: string[];
}

export interface Survey {
  id: string;
  title: Record<Language, string>;
  nodes: SurveyQuestion[];
  branches: Record<string, BranchQuestion>;
  metadata?: Record<string, unknown>;
}

export interface CodeRecord {
  code: string;
  type: 'NCO' | 'NIC' | 'ISIC';
  label: string;
  synonyms: string[];
  externalSource?: string;
}

export interface Persona {
  enumeratorId: string;
  speedSeconds: number[];
  answers: Record<string, string>;
  expectedConfidence: number;
  expectedTrust: TrustLevel;
  expectedFlags?: ValidationLayer[];
}

export interface SeedData {
  users: User[];
  enumerators: Enumerator[];
  households: Household[];
  survey: Survey;
  codes: CodeRecord[];
  referenceDistributions: {
    income: { p05: number; median: number; p95: number };
    responseTimeSeconds: { median: number };
  };
  trustWeights: {
    validation: number;
    fraud: number;
    evidence: number;
    behaviour: number;
  };
  personas: {
    genuine: Persona;
    suspicious: Persona;
  };
}

export interface ValidationLayer {
  layer: string;
  status: StatusLevel;
  reason: string;
}

export interface CodeSuggestion {
  code: string;
  type: string;
  label: string;
  confidence: number;
  source: 'Local' | 'MoSPI NIC';
  reason: string;
}

export interface IntelligenceResult {
  confidence: number;
  trustLevel: TrustLevel;
  decision: 'ASK' | 'SIMPLIFY' | 'SKIP' | 'REORDER';
  nextQuestionId?: string;
  reason: string;
  layers: ValidationLayer[];
  scores: {
    engagement: number;
    fatigue: number;
    dropout: number;
    quality: number;
  };
  breakdown: {
    validation: number;
    fraud: number;
    evidence: number;
    behaviour: number;
  };
  suggestion?: CodeSuggestion;
  stored: boolean;
}

export interface LiveFlag {
  id: string;
  enumeratorId: string;
  enumeratorName: string;
  survey: string;
  reason: string;
  trustScore: number;
  trustLevel: TrustLevel;
  timestamp: string;
}

export interface AnalyticsSnapshot {
  responsesToday: number;
  flagged: number;
  averageConfidence: number;
  activeEnumerators: number;
  totalResponses: number;
  validatedRate: number;
  errorRate: number;
  ruralUrban: [number, number];
  genderRatio: { male: number; female: number };
  confidenceScore: number;
  stateValidation: Array<{ state: string; rate: number }>;
  enumeratorRanking: Array<Enumerator & { responses: number; errorRate: number; flaggedRate: number }>;
  responseTrend: Array<{ label: string; responses: number; flagged: number }>;
  sectorDistribution: Array<{ sector: string; value: number }>;
  confidenceDistribution: Array<{ bucket: string; count: number }>;
}

export interface ApiResponse<T> {
  data: T;
  source: 'api' | 'seed';
}
