import { Survey, Enumerator, ClassificationCode, SurveyResponse, User, IntelligenceSession, NationalMetrics, Question, ValidationRule } from './types';
import { INITIAL_QUESTION_BANK, CLASSIFICATION_CODES, INITIAL_SURVEYS, INITIAL_ENUMERATORS, INITIAL_RESPONSES } from './mockData';

const API_BASE = '/api';

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('satark_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    let detail = '';
    try {
      const body = await response.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      detail = await response.text().catch(() => '');
    }
    throw new Error(`API Error ${response.status}${detail ? `: ${detail}` : ''}`);
  }

  return response.json();
}

// Mappings from database structures (title/nodes/rules) to new frontend structures (name_en/questions/validationRules)
function mapDbValidationRuleToFe(vr: any): ValidationRule {
  return {
    id: vr.id || `rule_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
    type: (vr.rule_type || vr.type || 'range') as any,
    fieldName: vr.field || vr.fieldName || '',
    expression: vr.params ? JSON.stringify(vr.params) : (vr.expression || ''),
    reason: vr.reason_template || vr.reason || '',
    severity: (vr.severity === 'fail' ? 'fail' : 'warn') as any
  };
}

function mapFeValidationRuleToDb(vr: ValidationRule, surveyId: string): any {
  let params: Record<string, any> = {};
  try {
    params = JSON.parse(vr.expression);
  } catch {
    params = { expression: vr.expression };
  }
  return {
    id: vr.id,
    survey_id: surveyId,
    field: vr.fieldName,
    rule_type: vr.type,
    params,
    severity: vr.severity,
    reason_template: vr.reason
  };
}

function mapDbQuestionToFe(q: any): Question {
  const rules = q.rules || {};
  const validationRules: ValidationRule[] = [];
  
  if (rules.range) {
    validationRules.push({
      id: `range_${q.id}`,
      type: 'range',
      fieldName: q.code || q.id,
      expression: `value >= ${rules.range[0]} && value <= ${rules.range[1]}`,
      reason: `Value must be between ${rules.range[0]} and ${rules.range[1]}`,
      severity: 'fail'
    });
  }
  if (rules.crossField) {
    validationRules.push({
      id: `cross_${q.id}`,
      type: 'cross',
      fieldName: q.code || q.id,
      expression: `Q_OCCUPATION === "${rules.crossField.ifOccupation}" ? value <= ${rules.crossField.max} : true`,
      reason: `Maximum for ${rules.crossField.ifOccupation} is ${rules.crossField.max}`,
      severity: 'warn'
    });
  }

  return {
    id: q.id,
    block: q.block || 'Block 1: Survey Data',
    code: q.code || q.id,
    text_en: q.q?.en || '',
    text_hi: q.q?.hi || '',
    text_ta: q.q?.ta || '',
    type: q.type === 'choice' ? 'single' : q.type,
    options: q.options || [],
    options_hi: q.options_hi || q.options || [],
    options_ta: q.options_ta || q.options || [],
    conditionalShow: q.conditionalShow || '',
    autoCodeAs: q.codeType || 'None',
    validationRules: validationRules
  };
}

function mapFeQuestionToDb(q: Question): any {
  let rangeRule: any = undefined;
  let crossFieldRule: any = undefined;

  q.validationRules?.forEach(vr => {
    if (vr.type === 'range') {
      const matches = vr.expression.match(/value\s*>=\s*(\d+)\s*&&\s*value\s*<=\s*(\d+)/);
      if (matches) {
        rangeRule = [Number(matches[1]), Number(matches[2])];
      }
    }
    if (vr.type === 'cross') {
      const matches = vr.expression.match(/Q_OCCUPATION\s*===\s*"([^"]+)"\s*\?\s*value\s*<=\s*(\d+)\s*:\s*true/);
      if (matches) {
        crossFieldRule = {
          ifOccupation: matches[1],
          max: Number(matches[2])
        };
      }
    }
  });

  return {
    id: q.id,
    type: q.type === 'single' ? 'choice' : q.type,
    codeType: q.autoCodeAs === 'None' ? null : q.autoCodeAs,
    options: q.options || [],
    options_hi: q.options_hi || [],
    options_ta: q.options_ta || [],
    block: q.block,
    code: q.code,
    q: {
      en: q.text_en,
      hi: q.text_hi,
      ta: q.text_ta
    },
    rules: {
      ...(rangeRule ? { range: rangeRule } : {}),
      ...(crossFieldRule ? { crossField: crossFieldRule } : {})
    }
  };
}

function mapDbSurveyToFe(s: any): Survey {
  return {
    id: s.id,
    name_en: s.title?.en || s.id,
    name_hi: s.title?.hi || '',
    name_ta: s.title?.ta || '',
    version: s.version ? String(s.version) : '1.0.0',
    status: s.status === 'published' ? 'Published' : 'Draft',
    questions: (s.nodes || []).filter((n: any) => n.type !== 'adaptive').map(mapDbQuestionToFe)
  };
}

function mapFeSurveyToDb(s: Survey): any {
  return {
    id: s.id,
    title: {
      en: s.name_en,
      hi: s.name_hi,
      ta: s.name_ta
    },
    nodes: s.questions.map(mapFeQuestionToDb),
    branches: {},
    metadata: {}
  };
}

function mapDbResponseToFe(r: any): SurveyResponse {
  const layers = r.validationFlags || r.intelligence?.layers || [];
  const getLayer = (name: string) => {
    const l = layers.find((x: any) => x.layer.toLowerCase().includes(name.toLowerCase())) || { status: 'pass', reason: 'Verified.' };
    return { status: l.status as any, reason: l.reason };
  };

  const confidence = r.trust?.confidence ?? r.qualityScore ?? r.trustScore ?? 80;
  const statusVal = r.status === 'approved' ? 'approved' : r.status === 're-interview' ? 're-interview' : 'flagged';

  return {
    id: r.id,
    surveyId: r.surveyId || 'sur_plfs_2026',
    surveyName: r.survey || r.surveyTitle || 'Periodic Labour Force Survey (PLFS)',
    enumeratorId: r.enumeratorId || 'enum_1',
    enumeratorName: r.enumeratorName || 'Lakshmi R.',
    householdId: r.householdId || 'HH-TN-0042',
    timestamp: r.timestamp || r.createdAt || new Date().toISOString(),
    answers: r.answers || {},
    codedAnswers: r.codedAnswers || {
      Q_OCCUPATION: {
        code: r.approvedCode || 'None',
        label: r.approvedLabel || 'Uncoded freeform text',
        confidence: 100,
        reason: 'Manual validation registry code'
      }
    },
    consentLogged: true,
    paradata: {
      timePerQuestion: r.paradata?.questionTimings || {},
      corrections: r.paradata?.correctionCount || 0,
      navBackCount: r.paradata?.backNavCount || 0,
      interruptedCount: 0,
      gpsLat: r.paradata?.gpsLatitude || 13.0827,
      gpsLng: r.paradata?.gpsLongitude || 80.2707,
      mode: (r.paradata?.mode as any) || 'CAPI'
    },
    behaviorScores: {
      engagement: r.intelligence?.scores?.engagement || 95,
      fatigue: r.intelligence?.scores?.fatigue || 15,
      dropout: r.intelligence?.scores?.dropout || 5,
      quality: r.intelligence?.scores?.quality || 94
    },
    validation: {
      layer1_rule: getLayer('rule') || getLayer('verdict'),
      layer2_govt: getLayer('govt') || getLayer('lgd'),
      layer3_bayesian: getLayer('bayesian') || getLayer('outlier'),
      layer4_behavior: getLayer('behavior') || getLayer('timing') || getLayer('pacing'),
      layer5_cross: getLayer('cross')
    },
    confidenceScore: confidence,
    trustBand: (r.trustLevel || (confidence >= 80 ? 'Green' : confidence >= 50 ? 'Amber' : 'Red')) as any,
    status: statusVal
  };
}

function mapDbIntelligenceToFe(intel: any, sessionId: string, answers: any, paradata: any): IntelligenceSession {
  const layers = intel?.layers || [];
  const getLayer = (name: string) => {
    const l = layers.find((x: any) => x.layer.toLowerCase().includes(name.toLowerCase())) || { status: 'pass', reason: 'Verified.' };
    return { status: l.status as any, reason: l.reason };
  };

  return {
    sessionId: sessionId,
    currentStep: Object.keys(answers).length,
    answers,
    paradata,
    behaviorScores: {
      engagement: intel?.scores?.engagement ?? 100,
      fatigue: intel?.scores?.fatigue ?? 0,
      dropout: intel?.scores?.dropout ?? 0,
      quality: intel?.scores?.quality ?? 100
    },
    validation: {
      layer1_rule: getLayer('rule') || getLayer('verdict'),
      layer2_govt: getLayer('govt') || getLayer('lgd'),
      layer3_bayesian: getLayer('bayesian') || getLayer('outlier'),
      layer4_behavior: getLayer('behavior') || getLayer('timing') || getLayer('pacing'),
      layer5_cross: getLayer('cross')
    },
    confidenceScore: intel?.confidence ?? 100,
    trustBand: (intel?.trustLevel ?? 'Green') as any,
    nextAction: intel?.decision ?? 'ASK',
    nextActionReason: intel?.reason ?? 'Normal execution flow'
  };
}

class LocalDB {
  surveys: Survey[] = [];
  enumerators: Enumerator[] = [];
  responses: SurveyResponse[] = [];
  currentUser: User | null = null;
  callbacks: ((event: string, data: any) => void)[] = [];

  constructor() {
    this.init();
  }

  init() {
    const savedUser = localStorage.getItem('satark_current_user');
    if (savedUser) {
      this.currentUser = JSON.parse(savedUser);
    }
  }

  async saveSurveys() {
    // Sync surveys dynamically with the database
    for (const s of this.surveys) {
      const dbSurvey = mapFeSurveyToDb(s);
      await request<any>(`/surveys/${s.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title: dbSurvey.title,
          question_graph: dbSurvey
        })
      });
    }
  }

  saveEnumerators() {
    // Managed on backend
  }

  saveResponses() {
    // Managed on backend
  }

  subscribe(cb: (event: string, data: any) => void) {
    this.callbacks.push(cb);
    return () => {
      this.callbacks = this.callbacks.filter(c => c !== cb);
    };
  }

  emit(event: string, data: any) {
    this.callbacks.forEach(cb => {
      try {
        cb(event, data);
      } catch (e) {
        console.error(e);
      }
    });
  }
}

export const db = new LocalDB();

export function resolveAutoCoding(occupationText: string): { code: string; label: string; confidence: number; reason: string } | null {
  const query = occupationText.toLowerCase().trim();
  if (!query) return null;

  const matched = CLASSIFICATION_CODES.find(code => 
    code.synonyms.some(syn => query.includes(syn.toLowerCase())) ||
    code.label_en.toLowerCase().includes(query) ||
    code.label_hi.toLowerCase().includes(query) ||
    code.label_ta.toLowerCase().includes(query)
  );

  if (matched) {
    return {
      code: matched.code,
      label: matched.label_en,
      confidence: 96,
      reason: `Matched official MoSPI semantic dictionary taxonomy '${matched.label_en}' (Code: ${matched.code})`
    };
  }

  return {
    code: 'None',
    label: 'Unclassified Free-Text',
    confidence: 30,
    reason: 'Syntactic matching low; routed to DPD Officer manual queue'
  };
}

// Global variable to hold conversational session id
let currentSessionId: string | null = null;

export const api = {
  // Authentication
  async login(username: string): Promise<User> {
    const passwords: Record<string, string> = {
      admin: 'admin123',
      sdrd: 'design123',
      fod: 'field123',
      dpd: 'process123',
      scd: 'coord123'
    };
    const password = passwords[username.toLowerCase()] || 'demo_password';

    const res = await request<{ user: any; token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });

    const user: User = {
      id: res.user.id,
      name: res.user.name,
      role: res.user.role as any,
      region: res.user.region || 'Tamil Nadu'
    };

    db.currentUser = user;
    localStorage.setItem('satark_current_user', JSON.stringify(user));
    localStorage.setItem('satark_token', res.token);
    return user;
  },

  async logout(): Promise<void> {
    db.currentUser = null;
    localStorage.removeItem('satark_current_user');
    localStorage.removeItem('satark_token');
  },

  getCurrentUser(): User | null {
    return db.currentUser;
  },

  // Surveys
  async getSurveys(): Promise<Survey[]> {
    const res = await request<{ surveys: any[] }>('/surveys');
    const list = res.surveys.map(mapDbSurveyToFe);
    db.surveys = list;
    return list;
  },

  async createSurvey(survey: Survey): Promise<Survey> {
    const dbSurvey = mapFeSurveyToDb(survey);
    const res = await request<{ survey: any }>('/surveys', {
      method: 'POST',
      body: JSON.stringify(dbSurvey)
    });
    const mapped = mapDbSurveyToFe(res.survey);
    // Insert into db local cache
    db.surveys = db.surveys.filter(s => s.id !== mapped.id);
    db.surveys.push(mapped);
    return mapped;
  },

  async saveSurvey(survey: Survey): Promise<Survey> {
    const dbSurvey = mapFeSurveyToDb(survey);
    try {
      const res = await request<{ survey: any }>('/surveys', {
        method: 'POST',
        body: JSON.stringify(dbSurvey)
      });
      const mapped = mapDbSurveyToFe(res.survey);
      db.surveys = db.surveys.filter(s => s.id !== mapped.id);
      db.surveys.push(mapped);
      return mapped;
    } catch (err: any) {
      if (err.message && (err.message.includes('409') || err.message.includes('Conflict'))) {
        const res = await request<{ survey: any }>(`/surveys/${survey.id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            title: dbSurvey.title,
            question_graph: dbSurvey
          })
        });
        const mapped = mapDbSurveyToFe(res.survey);
        db.surveys = db.surveys.map(s => s.id === survey.id ? mapped : s);
        return mapped;
      }
      throw err;
    }
  },

  async generateSurveyFromPrompt(prompt: string): Promise<Survey> {
    const res = await request<{ survey: any }>('/surveys/generate', {
      method: 'POST',
      body: JSON.stringify({ prompt })
    });
    const mapped = mapDbSurveyToFe(res.survey);
    // Ensure the generated survey gets a unique ID to prevent conflicts with already published surveys
    mapped.id = `sur_gen_${Date.now()}`;
    return mapped;
  },

  async publishSurvey(surveyId: string): Promise<Survey> {
    const res = await request<{ survey_id: string; status: string; version: number }>(`/surveys/${surveyId}/publish`, {
      method: 'POST'
    });
    const surveys = await api.getSurveys();
    const published = surveys.find(s => s.id === surveyId);
    if (published) {
      return published;
    }
    const mapped: Survey = {
      id: surveyId,
      name_en: 'Survey',
      name_hi: '',
      name_ta: '',
      version: String(res.version || '1.0.0'),
      status: 'Published',
      questions: []
    };
    return mapped;
  },

  async submitConsent(surveyId: string, householdId: string, enumeratorId: string, consented: boolean, language: string): Promise<any> {
    return request<any>('/consent', {
      method: 'POST',
      body: JSON.stringify({ surveyId, householdId, enumeratorId, consented, language })
    });
  },

  async prepopulate(householdId: string): Promise<any> {
    return request<any>('/prepopulate', {
      method: 'POST',
      body: JSON.stringify({ householdId })
    });
  },

  async getQuestionBank(): Promise<Question[]> {
    const res = await request<{ questions: any[] }>('/question-bank');
    return res.questions.map(mapDbQuestionToFe);
  },

  async getClassificationCodes(): Promise<ClassificationCode[]> {
    const res = await request<{ codes: any[] }>('/codes?limit=1000');
    return res.codes.map((c: any) => ({
      code: c.code,
      type: c.type,
      label_en: c.label || '',
      label_hi: c.label_hi || c.label || '',
      label_ta: c.label_ta || c.label || '',
      synonyms: c.synonyms || []
    }));
  },

  // Conversational collection answering steps
  async evaluateAnsweringStep(
    surveyId: string,
    answers: Record<string, any>,
    paradata: { timePerQuestion: Record<string, number>; corrections: number; navBackCount: number },
    persona: 'Genuine' | 'Suspicious',
    speed: 'Normal' | 'Too-fast'
  ): Promise<IntelligenceSession> {
    // If we don't have a session ID yet, start one
    if (!currentSessionId) {
      const startRes = await request<{ sessionId: string }>('/collection/sessions/start', {
        method: 'POST',
        body: JSON.stringify({ surveyId })
      });
      currentSessionId = startRes.sessionId;
    }

    // Determine currently active question key
    const keys = Object.keys(answers);
    const activeQuestionId = keys[keys.length - 1] || 'Q_NAME';
    const elapsedSeconds = (paradata.timePerQuestion[activeQuestionId] || 1000) / 1000;

    // Post answer to collection session
    const res = await request<{ intelligence: any; sessionId: string }>(`/collection/sessions/${currentSessionId}/answer`, {
      method: 'POST',
      body: JSON.stringify({
        questionId: activeQuestionId,
        value: String(answers[activeQuestionId]),
        elapsedSeconds,
        correctionCount: paradata.corrections,
        backNavCount: paradata.navBackCount
      })
    });

    return mapDbIntelligenceToFe(res.intelligence, currentSessionId, answers, {
      ...paradata,
      interruptedCount: 0,
      gpsLat: 13.0827,
      gpsLng: 80.2707,
      mode: 'CAPI'
    });
  },

  async submitResponse(resp: SurveyResponse): Promise<SurveyResponse> {
    if (!currentSessionId) {
      // Fallback: direct response submit if session wasn't started
      const durationSeconds = Object.values(resp.paradata.timePerQuestion).reduce((a, b) => a + b, 0) / 1000;
      const res = await request<any>(`/surveys/${resp.surveyId}/responses`, {
        method: 'POST',
        body: JSON.stringify({
          surveyId: resp.surveyId,
          householdId: resp.householdId,
          enumeratorId: resp.enumeratorId,
          answers: resp.answers,
          channel: 'web',
          durationSeconds,
          gpsLatitude: resp.paradata.gpsLat || 13.0827,
          gpsLongitude: resp.paradata.gpsLng || 80.2707
        })
      });
      return {
        ...resp,
        id: res.response_id,
        confidenceScore: res.quality_score,
        trustBand: res.trustLevel,
        status: res.status
      };
    }

    // Complete active collection session
    const res = await request<{ responseId: string; qualityScore: number; trustLevel: string; status: string }>(
      `/collection/sessions/${currentSessionId}/complete`,
      { method: 'POST' }
    );

    // Reset current session id for next round
    currentSessionId = null;

    const finalResult = {
      ...resp,
      id: res.responseId,
      confidenceScore: res.qualityScore,
      trustBand: res.trustLevel as any,
      status: res.status as any
    };

    // Trigger local events
    db.emit('response.stored', { id: finalResult.id, trustBand: finalResult.trustBand });
    if (finalResult.trustBand === 'Red') {
      db.emit('flag.created', {
        id: finalResult.id,
        enumeratorName: finalResult.enumeratorName,
        surveyName: finalResult.surveyName,
        reason: 'Verification validation failed.',
        confidence: finalResult.confidenceScore,
        timestamp: new Date().toISOString()
      });
    }

    return finalResult;
  },

  async getResponses(status?: string): Promise<SurveyResponse[]> {
    const res = await request<{ responses: any[] }>(`/responses${status ? `?status=${status}` : ''}`);
    const list = res.responses.map(mapDbResponseToFe);
    db.responses = list;
    return list;
  },

  async approveResponse(id: string): Promise<void> {
    await request(`/responses/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ action: 'approve', reason: 'Approved via DPD review' })
    });
  },

  async flagResponseForReinterview(id: string): Promise<void> {
    await request(`/responses/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ action: 're_interview', reason: 'Sent for re-interview via DPD review' })
    });
  },

  // Enumerators List
  async getEnumerators(): Promise<Enumerator[]> {
    const res = await request<{ enumerators: any[] }>('/enumerators');
    const list = res.enumerators.map((e: any) => ({
      id: e.id,
      name: e.name,
      region: e.region,
      assignedCount: e.assigned || 0,
      completedCount: e.completed || 0,
      trustScore: e.trust_score || 100,
      sparkline: e.trust_trend || [100, 100, 100, 100, 100, 100, 100],
      recentFlags: []
    }));
    db.enumerators = list;
    return list;
  },

  // Assignments List
  async getAssignments(surveyId?: string, enumeratorId?: string, status?: string): Promise<any[]> {
    const params = new URLSearchParams();
    if (surveyId) params.append('survey_id', surveyId);
    if (enumeratorId) params.append('enumerator_id', enumeratorId);
    if (status) params.append('status', status);
    const qs = params.toString();
    const res = await request<{ assignments: any[] }>(`/assignments${qs ? `?${qs}` : ''}`);
    return res.assignments;
  },

  async createAssignments(surveyId: string, enumeratorIds: string[], householdIds: string[]): Promise<any[]> {
    const res = await request<{ assignments: any[] }>('/assignments', {
      method: 'POST',
      body: JSON.stringify({ surveyId, enumeratorIds, householdIds })
    });
    return res.assignments;
  },

  async updateAssignmentStatus(assignmentId: string, status: string): Promise<any> {
    const res = await request<{ assignment: any }>(`/assignments/${assignmentId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status })
    });
    return res.assignment;
  },

  // RAG query & ingest
  async ragQuery(bucket: string, question: string): Promise<any> {
    return request<any>('/rag/query', {
      method: 'POST',
      body: JSON.stringify({ bucket, question })
    });
  },

  async ragIngest(file: File, bucket: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('bucket', bucket);
    
    const token = localStorage.getItem('satark_token');
    const headers = token ? { Authorization: `Bearer ${token}` } : {};

    const response = await fetch('/api/rag/ingest', {
      method: 'POST',
      headers: headers,
      body: formData
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => '');
      throw new Error(`RAG Ingest Error ${response.status}: ${detail}`);
    }

    return response.json();
  },

  // Manual NCO code adjustment
  async updateResponseCoding(responseId: string, questionId: string, code: string, label: string): Promise<void> {
    await request('/coding/review', {
      method: 'POST',
      body: JSON.stringify({
        responseId,
        field: questionId,
        approvedCode: code,
        approvedLabel: label,
        approved: true
      })
    });
  },

  // Command metrics dashboard calculations
  async getNationalMetrics(minConfidence: number = 0): Promise<NationalMetrics & { filteredResponses: SurveyResponse[] }> {
    const res = await request<{
      responsesToday: number;
      flagged: number;
      averageConfidence: number;
      activeEnumerators: number;
    }>('/dashboard/metrics');

    const allResponses = await this.getResponses();
    const filteredResponses = allResponses.filter(r => r.confidenceScore >= minConfidence);

    return {
      responsesToday: res.responsesToday || filteredResponses.length,
      flaggedCount: res.flagged || filteredResponses.filter(r => r.trustBand === 'Red').length,
      avgConfidence: res.averageConfidence || 0,
      activeEnumerators: res.activeEnumerators || 5,
      filteredResponses
    };
  }
};
