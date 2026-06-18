/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Survey, Enumerator, ClassificationCode, SurveyResponse, PincodeLocation, CollectionChannel } from './types';

export const SEED_USERS = [
  { username: 'hsd', role: 'hsd', name: 'Priya Sharma', region: 'Household Survey Division' },
  { username: 'ensd', role: 'ensd', name: 'Ravi Menon', region: 'Enterprise Survey Division' },
  { username: 'fod', role: 'fod', name: 'R. K. Swamy', region: 'Field Operations Division' },
  { username: 'cqcd', role: 'cqcd', name: 'Asha Nair', region: 'Collection & Quality Control Division' },
  { username: 'diid', role: 'diid', name: 'Dr. Meena Iyer', region: 'Data Informatics & Innovation Division' },
  { username: 'aspd', role: 'aspd', name: 'Amit Verma', region: 'Analytics & Statistical Products Division' },
  { username: 'cicd', role: 'cicd', name: 'N. K. Rao', region: 'Central Informatics Coordination Division' },
  { username: 'cdd', role: 'cdd', name: 'Farah Khan', region: 'Coordination & Dissemination Division' }
];

export const CLASSIFICATION_CODES: ClassificationCode[] = [
  {
    code: '8322',
    type: 'NCO',
    label_en: 'Auto-rickshaw Driver and Taxi Drivers',
    label_hi: 'ऑटो रिक्शा चालक और टैक्सी चालक',
    label_ta: 'ஆட்டோ ரிக்ஷா மற்றும் டாக்ஸி ஓட்டுநர்கள்',
    synonyms: ['auto', 'auto driver', 'taxi driver', 'ஆட்டோ', 'ஆட்டோ ஓட்டுநர்', 'ऑटो ड्राइवर', 'rickshaw', 'cab']
  },
  {
    code: '01111',
    type: 'NIC',
    label_en: 'Growing of wheat',
    label_hi: 'गेहूं की खेती',
    label_ta: 'கோதுமை வளர்ப்பு',
    synonyms: ['wheat', 'farming', 'wheat farmer', 'कृषि', 'गेहूं', 'கோதுமை', 'விவசாயம்']
  },
  {
    code: '49224',
    type: 'NIC',
    label_en: 'Taxi operation / cab services',
    label_hi: 'टैक्सी संचालन / कैब सेवाएं',
    label_ta: 'டாக்ஸி மற்றும் கேப் சேவைகள்',
    synonyms: ['taxi service', 'cab service', 'uber', 'ola', 'டாக்ஸி', 'टैक्सी']
  },
  {
    code: '15110',
    type: 'ISIC',
    label_en: 'Production and processing of meat',
    label_hi: 'मांस का उत्पादन और प्रसंस्करण',
    label_ta: 'இறைச்சி உற்பத்தி மற்றும் பதப்படுத்துதல்',
    synonyms: ['meat', 'butcher', 'slaughterhouse', 'மாமிசம்', 'मांस']
  }
];

export const REFERENCE_STATS = {
  medianIncome: 22000,
  p05Income: 6000,
  p95Income: 80000,
  medianResponseTimeSec: 90
};

export const INITIAL_QUESTION_BANK = [
  {
    id: 'qb_1',
    block: 'Block 1: General Info',
    code: 'Q_NAME',
    text_en: 'Full name of the respondent?',
    text_hi: 'उत्तरदाता का पूरा नाम?',
    text_ta: 'பதில் அளிப்பவரின் முழு பெயர்?',
    type: 'text' as const,
    validationRules: [
      { id: 'v1', type: 'required' as const, fieldName: 'Q_NAME', expression: 'true', reason: 'Respondent name is mandatory', severity: 'fail' as const }
    ]
  },
  {
    id: 'qb_2',
    block: 'Block 1: General Info',
    code: 'Q_AGE',
    text_en: 'Age of the respondent?',
    text_hi: 'उत्तरदाता की आयु?',
    text_ta: 'பதில் அளிப்பவரின் வயது?',
    type: 'number' as const,
    validationRules: [
      { id: 'v2', type: 'range' as const, fieldName: 'Q_AGE', expression: 'value >= 15 && value <= 110', reason: 'Age must be between 15 and 110 for PLFS interview eligibility', severity: 'fail' as const }
    ]
  },
  {
    id: 'qb_3',
    block: 'Block 2: Activity',
    code: 'Q_OCCUPATION',
    text_en: 'Primary occupation or activity status?',
    text_hi: 'प्राथमिक व्यवसाय या गतिविधि की स्थिति?',
    text_ta: 'முக்கிய தொழில் அல்லது செயல்பாடு நிலை?',
    type: 'single' as const,
    options: ['Farmer', 'Auto-rickshaw Driver', 'Unemployed', 'Student', 'Government Service'],
    options_hi: ['किसान', 'ऑटो रिक्शा चालक', 'बेरोजगार', 'छात्र', 'सरकारी नौकरी'],
    options_ta: ['விவசாயி', 'ஆட்டோ ஓட்டுநர்', 'வேலையில்லாதவர்', 'மாணவர்', 'அரசு வேலை'],
    autoCodeAs: 'NCO' as const
  },
  {
    id: 'qb_4',
    block: 'Block 2: Activity',
    code: 'Q_INCOME',
    text_en: 'Monthly income / value of self-consumption (₹)?',
    text_hi: 'मासिक आय / स्व-उपभोग मूल्य (₹)?',
    text_ta: 'மாதாந்திர வருமானம் / சுய-நுகர்வு மதிப்பு (₹)?',
    type: 'number' as const,
    validationRules: [
      { id: 'v3', type: 'range' as const, fieldName: 'Q_INCOME', expression: 'value >= 0 && value <= 500000', reason: 'Income must be within standard national household survey boundary', severity: 'fail' as const },
      { id: 'v4', type: 'cross' as const, fieldName: 'Q_INCOME', expression: '(Q_OCCUPATION === "Unemployed" || Q_OCCUPATION === "Student") ? value < 10000 : true', reason: 'High income (>=₹10,000) contradicts activity status (Unemployed / Student)', severity: 'fail' as const }
    ]
  },
  {
    id: 'qb_5',
    block: 'Block 2: Activity',
    code: 'Q_MOBILE',
    text_en: 'Do you own an active mobile internet connection?',
    text_hi: 'क्या आपके पास मोबाइल इंटरनेट कनेक्शन है?',
    text_ta: 'உங்களிடம் மொபைல் இணைய இணைப்பு உள்ளதா?',
    type: 'single' as const,
    options: ['Yes', 'No'],
    options_hi: ['हाँ', 'नहीं'],
    options_ta: ['ஆம்', 'இல்லை']
  }
];

const tracedQuestionBank = INITIAL_QUESTION_BANK.map((question, index) => ({
  ...question,
  sourceTrace: {
    source_document: index <= 3 ? 'NSS PLFS 2024-25 QBS' : 'NSS HCES 2023-24 QBS',
    section: question.block.replace(/^Block \d+:\s*/, ''),
    question_id: question.code,
    language: 'English',
    confidence: index <= 3 ? 94 : 89,
    retrieved_context: `${question.code} reused from official question bank after Survey Design review.`,
    generated_reason: 'Question retained because it is needed for household identification, routing, validation, or coding.'
  },
  generatedReason: 'Matched official survey precedent and validation requirements.',
  retrievalConfidence: index <= 3 ? 94 : 89
}));

export const OFFICIAL_COLLECTION_CHANNELS: CollectionChannel[] = [
  { id: 'mobile', label: 'Mobile App CAPI', status: 'Active', endpoint: '/api/collection/sessions', sessionsToday: 642, lastSync: '2 min ago' },
  { id: 'web', label: 'Web Survey', status: 'Ready', endpoint: '/api/collection/sessions', sessionsToday: 118, lastSync: '4 min ago' },
  { id: 'whatsapp', label: 'WhatsApp Survey', status: 'Active', endpoint: '/api/v1/channels/whatsapp', sessionsToday: 284, lastSync: '1 min ago' },
  { id: 'ivr', label: 'IVR Survey', status: 'Active', endpoint: '/api/v1/channels/ivr', sessionsToday: 96, lastSync: '6 min ago' },
  { id: 'voice_avatar', label: 'Voice Avatar Survey', status: 'Ready', endpoint: '/api/v1/channels/avatar', sessionsToday: 41, lastSync: '9 min ago' }
];

const lifecycle = (trust: number) => [
  { stage: 'Created' as const, status: 'complete' as const, records: '150 questions', issues: 0, trust, audit: 'Survey Design draft logged with source trace.' },
  { stage: 'Published' as const, status: 'complete' as const, records: 'Version frozen', issues: 0, trust, audit: 'Published questionnaire cannot be edited without a new version.' },
  { stage: 'Deployed' as const, status: 'complete' as const, records: '24 states', issues: 1, trust: trust - 1, audit: 'Field assignments generated by FOD.' },
  { stage: 'Collected' as const, status: 'active' as const, records: '1,24,000 HH', issues: 8, trust: trust - 3, audit: 'CAPI, Web, WhatsApp, IVR and Voice Avatar collection running.' },
  { stage: 'Validated' as const, status: 'active' as const, records: '1,16,000 HH', issues: 5, trust: trust - 2, audit: 'Validation rules and trust indicators stored.' },
  { stage: 'Processed' as const, status: 'pending' as const, records: '1,10,000 HH', issues: 3, trust: trust - 1, audit: 'C&QCD coding and review in progress.' },
  { stage: 'Approved' as const, status: 'pending' as const, records: '1,08,000 HH', issues: 1, trust, audit: 'Awaiting National Intelligence certification.' },
  { stage: 'Exported' as const, status: 'pending' as const, records: 'DDI XML ready', issues: 0, trust, audit: 'Export package not yet released.' }
];

export const INITIAL_SURVEYS: Survey[] = [
  {
    id: 'DDI-IND-MOSPI-PLFS26',
    ddiId: 'DDI-IND-MOSPI-PLFS26',
    shortName: 'PLFS 2026',
    year: '2026',
    organization: 'MoSPI',
    country: 'IND',
    surveyType: 'Labour Survey',
    coverageArea: 'Tamil Nadu',
    targetPopulation: 'Households and working-age persons',
    mode: 'Mixed',
    enumeratorCount: 150,
    coverage: 92,
    qualityScore: 96,
    issues: 2,
    lifecycle: lifecycle(96),
    channels: OFFICIAL_COLLECTION_CHANNELS,
    name_en: 'Periodic Labour Force Survey 2026',
    name_hi: 'आवधिक श्रम बल सर्वेक्षण 2026',
    name_ta: 'காலமுறை தொழிலாளர் கணக்கெடுப்பு 2026',
    version: '2.4.0',
    status: 'Published',
    questions: tracedQuestionBank
  },
  {
    id: 'DDI-IND-MOSPI-NSS-HCES26',
    ddiId: 'DDI-IND-MOSPI-NSS-HCES26',
    shortName: 'HCES 2026',
    year: '2026',
    organization: 'MoSPI',
    country: 'IND',
    surveyType: 'Household Consumption Survey',
    coverageArea: 'All India',
    targetPopulation: 'Households',
    mode: 'Mixed',
    enumeratorCount: 220,
    coverage: 88,
    qualityScore: 92,
    issues: 5,
    lifecycle: lifecycle(92),
    channels: OFFICIAL_COLLECTION_CHANNELS,
    name_en: 'Household Consumer Expenditure Survey 2026',
    name_hi: 'घरेलू उपभोक्ता व्यय सर्वेक्षण 2026',
    name_ta: 'வீட்டு நுகர்வு செலவு கணக்கெடுப்பு 2026',
    version: '1.8.0',
    status: 'Published',
    questions: tracedQuestionBank.slice(0, 4)
  },
  {
    id: 'DDI-IND-MOSPI-ASUSE26',
    ddiId: 'DDI-IND-MOSPI-ASUSE26',
    shortName: 'ASUSE 2026',
    year: '2026',
    organization: 'MoSPI',
    country: 'IND',
    surveyType: 'Enterprise Survey',
    coverageArea: 'Urban and rural enterprise clusters',
    targetPopulation: 'Unincorporated sector enterprises',
    mode: 'CAPI',
    enumeratorCount: 180,
    coverage: 94,
    qualityScore: 98,
    issues: 1,
    lifecycle: lifecycle(98),
    channels: OFFICIAL_COLLECTION_CHANNELS,
    name_en: 'Annual Survey of Unincorporated Sector Enterprises 2026',
    name_hi: 'Annual Survey of Unincorporated Sector Enterprises 2026',
    name_ta: 'Annual Survey of Unincorporated Sector Enterprises 2026',
    version: '1.2.0',
    status: 'Published',
    questions: tracedQuestionBank.slice(0, 3)
  },
  {
    id: 'DDI-IND-MOSPI-AGCENSUS26',
    ddiId: 'DDI-IND-MOSPI-AGCENSUS26',
    shortName: 'Agricultural Census',
    year: '2026',
    organization: 'MoSPI',
    country: 'IND',
    surveyType: 'Agriculture Survey',
    coverageArea: 'District level',
    targetPopulation: 'Farm households',
    mode: 'CAPI',
    enumeratorCount: 150,
    coverage: 91,
    qualityScore: 94,
    issues: 4,
    lifecycle: lifecycle(94),
    channels: OFFICIAL_COLLECTION_CHANNELS.filter(c => c.id !== 'web'),
    name_en: 'Agricultural Census 2026',
    name_hi: 'Agricultural Census 2026',
    name_ta: 'Agricultural Census 2026',
    version: '1.0.0',
    status: 'Published',
    questions: tracedQuestionBank.slice(0, 5)
  },
  {
    id: 'DDI-IND-MOSPI-ECONCENSUS26',
    ddiId: 'DDI-IND-MOSPI-ECONCENSUS26',
    shortName: 'Economic Census',
    year: '2026',
    organization: 'MoSPI',
    country: 'IND',
    surveyType: 'Enterprise Survey',
    coverageArea: 'All India economic establishments',
    targetPopulation: 'Establishments and enterprises',
    mode: 'Mixed',
    enumeratorCount: 260,
    coverage: 89,
    qualityScore: 93,
    issues: 6,
    lifecycle: lifecycle(93),
    channels: OFFICIAL_COLLECTION_CHANNELS,
    name_en: 'Economic Census 2026',
    name_hi: 'Economic Census 2026',
    name_ta: 'Economic Census 2026',
    version: '1.0.0',
    status: 'Published',
    questions: tracedQuestionBank.slice(0, 4)
  }
];

export const SURVEY_TYPES = [
  'Agriculture Survey',
  'Labour Survey',
  'Enterprise Survey',
  'Education Survey',
  'Health Survey',
  'Migration Survey',
  'Urban Survey',
  'Price Survey',
  'Environment Survey'
];

export const PINCODE_LOCATIONS: PincodeLocation[] = [
  { pincode: '515001', state: 'Andhra Pradesh', district: 'Anantapur', locality: 'Anantapur HO', stateLgdCode: '28', districtLgdCode: '502', lat: 14.6819, lng: 77.6006 },
  { pincode: '791111', state: 'Arunachal Pradesh', district: 'Papum Pare', locality: 'Itanagar', stateLgdCode: '12', districtLgdCode: '231', lat: 27.0844, lng: 93.6053 },
  { pincode: '781001', state: 'Assam', district: 'Kamrup Metropolitan', locality: 'Guwahati GPO', stateLgdCode: '18', districtLgdCode: '618', lat: 26.1445, lng: 91.7362 },
  { pincode: '800001', state: 'Bihar', district: 'Patna', locality: 'Patna GPO', stateLgdCode: '10', districtLgdCode: '230', lat: 25.5941, lng: 85.1376 },
  { pincode: '495001', state: 'Chhattisgarh', district: 'Bilaspur', locality: 'Bilaspur HO', stateLgdCode: '22', districtLgdCode: '375', lat: 22.0797, lng: 82.1409 },
  { pincode: '403001', state: 'Goa', district: 'North Goa', locality: 'Panaji', stateLgdCode: '30', districtLgdCode: '585', lat: 15.4909, lng: 73.8278 },
  { pincode: '380001', state: 'Gujarat', district: 'Ahmedabad', locality: 'Ahmedabad GPO', stateLgdCode: '24', districtLgdCode: '438', lat: 23.0225, lng: 72.5714 },
  { pincode: '122001', state: 'Haryana', district: 'Gurugram', locality: 'Gurugram HO', stateLgdCode: '06', districtLgdCode: '86', lat: 28.4595, lng: 77.0266 },
  { pincode: '171001', state: 'Himachal Pradesh', district: 'Shimla', locality: 'Shimla GPO', stateLgdCode: '02', districtLgdCode: '23', lat: 31.1048, lng: 77.1734 },
  { pincode: '834001', state: 'Jharkhand', district: 'Ranchi', locality: 'Ranchi GPO', stateLgdCode: '20', districtLgdCode: '364', lat: 23.3441, lng: 85.3096 },
  { pincode: '560001', state: 'Karnataka', district: 'Bengaluru Urban', locality: 'Bengaluru GPO', stateLgdCode: '29', districtLgdCode: '572', lat: 12.9716, lng: 77.5946 },
  { pincode: '682001', state: 'Kerala', district: 'Ernakulam', locality: 'Kochi', stateLgdCode: '32', districtLgdCode: '595', lat: 9.9312, lng: 76.2673 },
  { pincode: '462001', state: 'Madhya Pradesh', district: 'Bhopal', locality: 'Bhopal GPO', stateLgdCode: '23', districtLgdCode: '444', lat: 23.2599, lng: 77.4126 },
  { pincode: '400001', state: 'Maharashtra', district: 'Mumbai', locality: 'Mumbai GPO', stateLgdCode: '27', districtLgdCode: '519', lat: 18.9388, lng: 72.8354 },
  { pincode: '795001', state: 'Manipur', district: 'Imphal West', locality: 'Imphal HO', stateLgdCode: '14', districtLgdCode: '252', lat: 24.8170, lng: 93.9368 },
  { pincode: '793001', state: 'Meghalaya', district: 'East Khasi Hills', locality: 'Shillong GPO', stateLgdCode: '17', districtLgdCode: '274', lat: 25.5788, lng: 91.8933 },
  { pincode: '796001', state: 'Mizoram', district: 'Aizawl', locality: 'Aizawl HO', stateLgdCode: '15', districtLgdCode: '261', lat: 23.7271, lng: 92.7176 },
  { pincode: '797001', state: 'Nagaland', district: 'Kohima', locality: 'Kohima HO', stateLgdCode: '13', districtLgdCode: '246', lat: 25.6751, lng: 94.1086 },
  { pincode: '751001', state: 'Odisha', district: 'Khordha', locality: 'Bhubaneswar GPO', stateLgdCode: '21', districtLgdCode: '362', lat: 20.2961, lng: 85.8245 },
  { pincode: '143001', state: 'Punjab', district: 'Amritsar', locality: 'Amritsar GPO', stateLgdCode: '03', districtLgdCode: '49', lat: 31.6340, lng: 74.8723 },
  { pincode: '302001', state: 'Rajasthan', district: 'Jaipur', locality: 'Jaipur GPO', stateLgdCode: '08', districtLgdCode: '102', lat: 26.9124, lng: 75.7873 },
  { pincode: '737101', state: 'Sikkim', district: 'Gangtok', locality: 'Gangtok HO', stateLgdCode: '11', districtLgdCode: '225', lat: 27.3389, lng: 88.6065 },
  { pincode: '600001', state: 'Tamil Nadu', district: 'Chennai', locality: 'George Town', stateLgdCode: '33', districtLgdCode: '568', lat: 13.0827, lng: 80.2707 },
  { pincode: '600002', state: 'Tamil Nadu', district: 'Chennai', locality: 'Anna Salai', stateLgdCode: '33', districtLgdCode: '568', lat: 13.0649, lng: 80.2712 },
  { pincode: '600028', state: 'Tamil Nadu', district: 'Chennai', locality: 'Mylapore', stateLgdCode: '33', districtLgdCode: '568', lat: 13.0336, lng: 80.2687 },
  { pincode: '600040', state: 'Tamil Nadu', district: 'Chennai', locality: 'Anna Nagar', stateLgdCode: '33', districtLgdCode: '568', lat: 13.0878, lng: 80.2104 },
  { pincode: '641001', state: 'Tamil Nadu', district: 'Coimbatore', locality: 'Coimbatore HO', stateLgdCode: '33', districtLgdCode: '569', lat: 11.0168, lng: 76.9558 },
  { pincode: '625001', state: 'Tamil Nadu', district: 'Madurai', locality: 'Madurai HO', stateLgdCode: '33', districtLgdCode: '578', lat: 9.9252, lng: 78.1198 },
  { pincode: '500001', state: 'Telangana', district: 'Hyderabad', locality: 'Hyderabad GPO', stateLgdCode: '36', districtLgdCode: '507', lat: 17.3850, lng: 78.4867 },
  { pincode: '799001', state: 'Tripura', district: 'West Tripura', locality: 'Agartala GPO', stateLgdCode: '16', districtLgdCode: '269', lat: 23.8315, lng: 91.2868 },
  { pincode: '226001', state: 'Uttar Pradesh', district: 'Lucknow', locality: 'Lucknow GPO', stateLgdCode: '09', districtLgdCode: '157', lat: 26.8467, lng: 80.9462 },
  { pincode: '248001', state: 'Uttarakhand', district: 'Dehradun', locality: 'Dehradun GPO', stateLgdCode: '05', districtLgdCode: '60', lat: 30.3165, lng: 78.0322 },
  { pincode: '700001', state: 'West Bengal', district: 'Kolkata', locality: 'Kolkata GPO', stateLgdCode: '19', districtLgdCode: '342', lat: 22.5726, lng: 88.3639 },
  { pincode: '744101', state: 'Andaman and Nicobar Islands', district: 'South Andaman', locality: 'Port Blair', stateLgdCode: '35', districtLgdCode: '603', lat: 11.6234, lng: 92.7265 },
  { pincode: '160017', state: 'Chandigarh', district: 'Chandigarh', locality: 'Sector 17', stateLgdCode: '04', districtLgdCode: '55', lat: 30.7333, lng: 76.7794 },
  { pincode: '396230', state: 'Dadra and Nagar Haveli and Daman and Diu', district: 'Daman', locality: 'Daman HO', stateLgdCode: '26', districtLgdCode: '495', lat: 20.3974, lng: 72.8328 },
  { pincode: '110001', state: 'Delhi', district: 'New Delhi', locality: 'New Delhi GPO', stateLgdCode: '07', districtLgdCode: '94', lat: 28.6139, lng: 77.2090 },
  { pincode: '180001', state: 'Jammu and Kashmir', district: 'Jammu', locality: 'Jammu GPO', stateLgdCode: '01', districtLgdCode: '21', lat: 32.7266, lng: 74.8570 },
  { pincode: '194101', state: 'Ladakh', district: 'Leh', locality: 'Leh HO', stateLgdCode: '37', districtLgdCode: '9', lat: 34.1526, lng: 77.5771 },
  { pincode: '682555', state: 'Lakshadweep', district: 'Lakshadweep', locality: 'Kavaratti', stateLgdCode: '31', districtLgdCode: '587', lat: 10.5593, lng: 72.6358 },
  { pincode: '605001', state: 'Puducherry', district: 'Puducherry', locality: 'Puducherry HO', stateLgdCode: '34', districtLgdCode: '599', lat: 11.9416, lng: 79.8083 }
];

export const INITIAL_ENUMERATORS: Enumerator[] = [
  {
    id: 'enum_1',
    name: 'Lakshmi R.',
    region: 'Tamil Nadu (Chennai Central)',
    assignedCount: 165,
    completedCount: 154,
    trustScore: 92,
    sparkline: [90, 91, 91, 92, 92, 92, 92],
    recentFlags: []
  },
  {
    id: 'enum_2',
    name: 'Karthik S. (Suspect Profile)',
    region: 'Tamil Nadu (Chennai South)',
    assignedCount: 120,
    completedCount: 78,
    trustScore: 48,
    sparkline: [58, 55, 52, 49, 45, 42, 40],
    recentFlags: [
      {
        responseId: 'resp_seed_flagged',
        flagType: 'Speed / Contradiction',
        reason: 'Occupation was marked as Unemployed, but income reported was ₹2,00,000 in only 4 seconds of response time.',
        timestamp: '2026-06-07T10:00:00Z'
      }
    ]
  },
  {
    id: 'enum_3',
    name: 'Nandhini V.',
    region: 'Tamil Nadu (Mylapore 600028)',
    assignedCount: 148,
    completedCount: 139,
    trustScore: 96,
    sparkline: [93, 94, 95, 95, 96, 96, 96],
    recentFlags: []
  },
  {
    id: 'enum_4',
    name: 'Arun Prakash',
    region: 'Tamil Nadu (Anna Nagar 600040)',
    assignedCount: 132,
    completedCount: 119,
    trustScore: 88,
    sparkline: [84, 85, 86, 87, 88, 88, 88],
    recentFlags: []
  },
  {
    id: 'enum_5',
    name: 'Farida Begum',
    region: 'Tamil Nadu (George Town 600001)',
    assignedCount: 121,
    completedCount: 114,
    trustScore: 91,
    sparkline: [89, 90, 91, 91, 90, 91, 91],
    recentFlags: []
  },
  {
    id: 'enum_6',
    name: 'S. Manikandan',
    region: 'Tamil Nadu (Coimbatore 641001)',
    assignedCount: 118,
    completedCount: 103,
    trustScore: 82,
    sparkline: [80, 79, 81, 82, 83, 82, 82],
    recentFlags: []
  },
  {
    id: 'enum_7',
    name: 'Revathi M.',
    region: 'Tamil Nadu (Madurai 625001)',
    assignedCount: 96,
    completedCount: 92,
    trustScore: 95,
    sparkline: [91, 92, 93, 94, 95, 95, 95],
    recentFlags: []
  },
  {
    id: 'enum_8',
    name: 'Joseph Daniel',
    region: 'Tamil Nadu (Anna Salai 600002)',
    assignedCount: 104,
    completedCount: 86,
    trustScore: 74,
    sparkline: [78, 76, 75, 73, 74, 74, 74],
    recentFlags: []
  },
  {
    id: 'enum_9',
    name: 'Kavitha P.',
    region: 'Tamil Nadu (Mylapore 600028)',
    assignedCount: 88,
    completedCount: 81,
    trustScore: 87,
    sparkline: [83, 84, 85, 86, 87, 87, 87],
    recentFlags: []
  },
  {
    id: 'enum_10',
    name: 'Muthu Kumar',
    region: 'Tamil Nadu (George Town 600001)',
    assignedCount: 112,
    completedCount: 70,
    trustScore: 57,
    sparkline: [68, 65, 63, 60, 58, 57, 57],
    recentFlags: [
      {
        responseId: 'resp_seed_flagged',
        flagType: 'Speed warning',
        reason: 'Repeated interviews submitted below normal question reading time.',
        timestamp: '2026-06-07T11:10:00Z'
      }
    ]
  }
];

export const INITIAL_RESPONSES: SurveyResponse[] = [
  {
    id: 'resp_seed_1',
    surveyId: 'DDI-IND-MOSPI-PLFS26',
    surveyName: 'Periodic Labour Force Survey (PLFS-2026)',
    enumeratorId: 'enum_1',
    enumeratorName: 'Lakshmi R.',
    householdId: 'HH-TN-0042',
    timestamp: '2026-06-07T14:32:00Z',
    answers: {
      Q_NAME: 'Arun Kumar',
      Q_AGE: 34,
      Q_OCCUPATION: 'Auto-rickshaw Driver',
      Q_INCOME: 24500,
      Q_MOBILE: 'Yes'
    },
    codedAnswers: {
      Q_OCCUPATION: {
        code: '8322',
        label: 'Auto-rickshaw Driver',
        confidence: 96,
        reason: "Matched official NCO-2015 dictionary synonym 'auto driver'"
      }
    },
    consentLogged: true,
    consentTimestamp: '2026-06-07T14:30:10Z',
    paradata: {
      timePerQuestion: { Q_NAME: 15400, Q_AGE: 8600, Q_OCCUPATION: 22000, Q_INCOME: 18000, Q_MOBILE: 7200 },
      corrections: 1,
      navBackCount: 0,
      interruptedCount: 0,
      gpsLat: 13.0827,
      gpsLng: 80.2707,
      mode: 'CAPI'
    },
    behaviorScores: {
      engagement: 95,
      fatigue: 12,
      dropout: 5,
      quality: 94
    },
    validation: {
      layer1_rule: { status: 'pass', reason: 'Age eligibility and mandatory fields supplied.' },
      layer2_govt: { status: 'pass', reason: 'LGD State Code and NCO occupation code validated.' },
      layer3_bayesian: { status: 'pass', reason: 'Income at 54th percentile for occupation & geography bounds.' },
      layer4_behavior: { status: 'pass', reason: 'Time-per-question fits Indian household median standard.' },
      layer5_cross: { status: 'pass', reason: 'No cross-field contradictions observed.' }
    },
    confidenceScore: 94,
    trustBand: 'Green',
    status: 'approved'
  },
  {
    id: 'resp_seed_flagged',
    surveyId: 'DDI-IND-MOSPI-PLFS26',
    surveyName: 'Periodic Labour Force Survey (PLFS-2026)',
    enumeratorId: 'enum_2',
    enumeratorName: 'Karthik S. (Suspect Profile)',
    householdId: 'HH-TN-0043',
    timestamp: '2026-06-07T15:10:00Z',
    answers: {
      Q_NAME: 'Suresh Gopalan',
      Q_AGE: 21,
      Q_OCCUPATION: 'Unemployed',
      Q_INCOME: 200000,
      Q_MOBILE: 'Yes'
    },
    codedAnswers: {
      Q_OCCUPATION: {
        code: 'None',
        label: 'Unemployed',
        confidence: 100,
        reason: 'Direct match - no active NCO/NIC classification'
      }
    },
    consentLogged: true,
    consentTimestamp: '2026-06-07T15:09:55Z',
    paradata: {
      timePerQuestion: { Q_NAME: 1200, Q_AGE: 800, Q_OCCUPATION: 1100, Q_INCOME: 900, Q_MOBILE: 500 },
      corrections: 0,
      navBackCount: 0,
      interruptedCount: 0,
      gpsLat: 13.0482,
      gpsLng: 80.2214,
      mode: 'CAPI'
    },
    behaviorScores: {
      engagement: 14,
      fatigue: 90,
      dropout: 85,
      quality: 20
    },
    validation: {
      layer1_rule: { status: 'pass', reason: 'Fields entered successfully.' },
      layer2_govt: { status: 'pass', reason: 'Direct match resolved.' },
      layer3_bayesian: { status: 'fail', reason: 'Income ₹2,00,000 values lie beyond the 99.6th percentile of regional unemployment distribution.' },
      layer4_behavior: { status: 'fail', reason: 'Completed questions in 4.5 seconds (90 seconds national median).' },
      layer5_cross: { status: 'fail', reason: 'Income ₹2,00,000 exceeds ₹10,000 boundary for Unemployed occupation state.' }
    },
    confidenceScore: 46,
    trustBand: 'Red',
    status: 'flagged'
  }
];
