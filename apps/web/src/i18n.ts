import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

export const languageLabels = {
  en: 'EN',
  hi: 'हि',
  ta: 'த'
} as const;

i18n.use(initReactI18next).init({
  resources: {
    en: {
      translation: {
        signIn: 'Sign in to SATARK',
        tagline: 'Adaptive survey intelligence for trusted official statistics.',
        username: 'Username',
        password: 'Password',
        signInButton: 'Sign in',
        official: 'MoSPI official',
        realtime: 'Real-time',
        dashboard: 'Statistical Intelligence Dashboard',
        surveyDesign: 'Survey design',
        collectionOps: 'Collection operations',
        processing: 'Processing and coding',
        coordination: 'Monitoring and coordination',
        collectionClient: 'Collection client',
        commandCenter: 'Command center',
        qualityDashboard: 'Quality dashboard',
        analytics: 'Analytics',
        colorBlind: 'Color blind mode',
        signOut: 'Sign out',
        offline: 'Working offline - responses will sync when you reconnect',
        queued: '{{count}} queued',
        confidence: 'Confidence',
        reason: 'Reason',
        publishSurvey: 'Publish survey',
        generateDraft: 'Generate draft',
        consentTitle: 'Your consent',
        consentAccept: 'I consent',
        consentDecline: 'Decline',
        next: 'Next',
        complete: 'Complete survey'
      }
    },
    hi: {
      translation: {
        signIn: 'SATARK में साइन इन करें',
        tagline: 'विश्वसनीय आधिकारिक सांख्यिकी के लिए अनुकूली सर्वेक्षण बुद्धिमत्ता।',
        username: 'उपयोगकर्ता नाम',
        password: 'पासवर्ड',
        signInButton: 'साइन इन',
        official: 'MoSPI आधिकारिक',
        realtime: 'रीयल टाइम',
        dashboard: 'सांख्यिकीय इंटेलिजेंस डैशबोर्ड',
        surveyDesign: 'सर्वेक्षण डिजाइन',
        collectionOps: 'संग्रह संचालन',
        processing: 'प्रसंस्करण और कोडिंग',
        coordination: 'निगरानी और समन्वय',
        collectionClient: 'संग्रह क्लाइंट',
        commandCenter: 'कमांड सेंटर',
        qualityDashboard: 'गुणवत्ता डैशबोर्ड',
        analytics: 'विश्लेषण',
        colorBlind: 'कलर ब्लाइंड मोड',
        signOut: 'साइन आउट',
        offline: 'ऑफलाइन काम कर रहे हैं - प्रतिक्रियाएं कनेक्ट होने पर सिंक होंगी',
        queued: '{{count}} कतार में',
        confidence: 'विश्वास',
        reason: 'कारण',
        publishSurvey: 'सर्वेक्षण प्रकाशित करें',
        generateDraft: 'ड्राफ्ट बनाएं',
        consentTitle: 'आपकी सहमति',
        consentAccept: 'मैं सहमत हूं',
        consentDecline: 'अस्वीकार',
        next: 'आगे',
        complete: 'सर्वेक्षण पूरा करें'
      }
    },
    ta: {
      translation: {
        signIn: 'SATARK உள்நுழைவு',
        tagline: 'நம்பகமான அதிகாரப்பூர்வ புள்ளிவிவரங்களுக்கு தகவமைவு கணக்கெடுப்பு நுண்ணறிவு.',
        username: 'பயனர் பெயர்',
        password: 'கடவுச்சொல்',
        signInButton: 'உள்நுழைக',
        official: 'MoSPI அதிகாரப்பூர்வம்',
        realtime: 'நேரலை',
        dashboard: 'புள்ளிவிவர நுண்ணறிவு டாஷ்போர்டு',
        surveyDesign: 'கணக்கெடுப்பு வடிவமைப்பு',
        collectionOps: 'சேகரிப்பு செயல்பாடுகள்',
        processing: 'செயலாக்கம் மற்றும் குறியீடு',
        coordination: 'கண்காணிப்பு மற்றும் ஒருங்கிணைப்பு',
        collectionClient: 'சேகரிப்பு கிளையன்ட்',
        commandCenter: 'கட்டளை மையம்',
        qualityDashboard: 'தர டாஷ்போர்டு',
        analytics: 'பகுப்பாய்வு',
        colorBlind: 'வண்ண குருடு முறை',
        signOut: 'வெளியேறு',
        offline: 'ஆஃப்லைனில் வேலை செய்கிறது - பதில்கள் மீண்டும் இணைந்ததும் ஒத்திசைக்கப்படும்',
        queued: '{{count}} வரிசையில்',
        confidence: 'நம்பிக்கை',
        reason: 'காரணம்',
        publishSurvey: 'கணக்கெடுப்பை வெளியிடு',
        generateDraft: 'வரைவு உருவாக்கு',
        consentTitle: 'உங்கள் ஒப்புதல்',
        consentAccept: 'நான் ஒப்புக்கொள்கிறேன்',
        consentDecline: 'நிராகரி',
        next: 'அடுத்து',
        complete: 'கணக்கெடுப்பை முடிக்கவும்'
      }
    }
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false }
});

export default i18n;
