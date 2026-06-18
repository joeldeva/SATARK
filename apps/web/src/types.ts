/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type UserRole = 'hsd' | 'ensd' | 'fod' | 'cqcd' | 'diid' | 'aspd' | 'cicd' | 'cdd';

export interface User {
  id: string;
  name: string;
  role: UserRole;
  region: string;
}

export type QuestionType = 'single' | 'multi' | 'number' | 'text' | 'date';

export interface ValidationRule {
  id: string;
  type: 'range' | 'required' | 'cross' | 'regex';
  fieldName: string;
  expression: string; // e.g., "income < 50000" if occupation is student
  reason: string;     // Reason emitted if rule fails
  severity: 'fail' | 'warn';
}

export interface SourceTrace {
  source_document: string;
  section: string;
  question_id: string;
  language: string;
  confidence?: number;
  retrieved_context?: string;
  generated_reason?: string;
}

export interface Question {
  id: string;
  block: string; // e.g., "Block 1: Demographics"
  code: string;  // e.g., "Q1", "Q_OCCUPATION"
  text_en: string;
  text_hi: string;
  text_ta: string;
  translations?: Record<string, string>;
  type: QuestionType;
  options?: string[]; // English options
  options_hi?: string[];
  options_ta?: string[];
  options_i18n?: Record<string, string[]>;
  conditionalShow?: string; // expression like "Q_OCCUPATION !== 'Student'"
  autoCodeAs?: 'None' | 'NCO' | 'NIC' | 'ISIC';
  validationRules?: ValidationRule[];
  sourceTrace?: SourceTrace;
  generatedReason?: string;
  retrievalConfidence?: number;
}

export interface Survey {
  id: string;
  ddiId?: string;
  shortName?: string;
  year?: string;
  organization?: string;
  country?: string;
  surveyType?: string;
  coverageArea?: string;
  targetPopulation?: string;
  mode?: 'CAPI' | 'CATI' | 'Web' | 'WhatsApp' | 'IVR' | 'Voice Avatar' | 'Mixed';
  enumeratorCount?: number;
  coverage?: number;
  qualityScore?: number;
  issues?: number;
  lifecycle?: SurveyLifecycleStage[];
  channels?: CollectionChannel[];
  name_en: string;
  name_hi: string;
  name_ta: string;
  version: string;
  status: 'Draft' | 'Published';
  questions: Question[];
  languages?: string[];
  primaryLanguage?: string;
}

export interface SurveyLifecycleStage {
  stage: 'Created' | 'Published' | 'Deployed' | 'Collected' | 'Validated' | 'Processed' | 'Approved' | 'Exported';
  status: 'complete' | 'active' | 'pending' | 'issue';
  records: string;
  issues: number;
  trust: number;
  audit: string;
}

export interface PincodeLocation {
  pincode: string;
  state: string;
  district: string;
  locality: string;
  stateLgdCode?: string;
  districtLgdCode?: string;
  lat: number;
  lng: number;
}

export interface CollectionChannel {
  id: 'ivr' | 'whatsapp' | 'voice_avatar' | 'web' | 'mobile';
  label: string;
  status: 'Active' | 'Ready' | 'Paused';
  endpoint: string;
  sessionsToday: number;
  lastSync: string;
}

export interface ClassificationCode {
  code: string;
  type: 'NCO' | 'NIC' | 'ISIC' | 'LGD' | 'LGD_DISTRICT';
  label_en: string;
  label_hi: string;
  label_ta: string;
  synonyms: string[];
}

export interface Paradata {
  timePerQuestion: Record<string, number>; // questionId -> ms
  corrections: number; // backspaces/edits
  navBackCount: number; // back button presses
  interruptedCount: number; // window blur/resume
  gpsLat?: number;
  gpsLng?: number;
  mode: 'CAPI' | 'CATI' | 'Self';
}

export interface BehaviorScores {
  engagement: number; // 0-100
  fatigue: number;    // 0-100
  dropout: number;    // 0-100
  quality: number;    // 0-100
}

export interface ValidationStatus {
  layer1_rule: { status: 'pass' | 'fail' | 'warn'; reason: string }; // Standard rules
  layer2_govt: { status: 'pass' | 'fail' | 'warn'; reason: string }; // LGD / official codes
  layer3_bayesian: { status: 'pass' | 'fail' | 'warn'; reason: string }; // Statistical outlier
  layer4_behavior: { status: 'pass' | 'fail' | 'warn'; reason: string }; // Speed, straight-lining
  layer5_cross: { status: 'pass' | 'fail' | 'warn'; reason: string }; // Logical contradictions
}

// Per-method confidence + proof: which method ran, its score, and whether it flagged.
export interface ValidationMethod {
  name: string;            // Completeness | Range | Cross-field | Context | Behaviour
  method?: string;         // human description of the technique used
  status: 'pass' | 'fail' | 'warn' | string;
  reason: string;          // plain-language proof
  confidence?: number;     // 0..100
  flagged?: boolean;
}

export interface SurveyResponse {
  id: string;
  surveyId: string;
  surveyName: string;
  enumeratorId: string;
  enumeratorName: string;
  householdId: string;
  timestamp: string;
  answers: Record<string, any>; // questionId -> literal value
  codedAnswers: Record<string, { code: string; label: string; confidence: number; reason: string }>; // questionId -> code suggestions
  consentLogged: boolean;
  consentTimestamp?: string;
  paradata: Paradata;
  behaviorScores: BehaviorScores;
  validation: ValidationStatus;
  methods?: ValidationMethod[]; // per-method confidence + proof
  flaggedBy?: string[];
  confidenceScore: number; // Computed 0-100
  trustBand: 'Green' | 'Amber' | 'Red';
  status: 'approved' | 'flagged' | 're-interview';
  nicCode?: string;
  occupation?: string;
}

export interface Enumerator {
  id: string;
  name: string;
  region: string;
  assignedCount: number;
  completedCount: number;
  trustScore: number; // Cumulative 0-100
  sparkline: number[]; // Last 7 days trust scores
  recentFlags: {
    responseId: string;
    flagType: string;
    reason: string;
    timestamp: string;
  }[];
}

export interface IntelligenceSession {
  sessionId: string;
  currentStep: number;
  answers: Record<string, any>;
  paradata: Paradata;
  behaviorScores: BehaviorScores;
  validation: ValidationStatus;
  methods?: ValidationMethod[]; // per-method confidence + proof
  flaggedBy?: string[];
  confidenceScore: number;
  trustBand: 'Green' | 'Amber' | 'Red';
  nextAction: 'ASK' | 'SIMPLIFY' | 'SKIP' | 'REORDER';
  nextActionReason: string;
  nextQuestionId?: string;
  visibleQueue?: string[];
}

export interface NationalMetrics {
  responsesToday: number;
  flaggedCount: number;
  avgConfidence: number;
  activeEnumerators: number;
}
