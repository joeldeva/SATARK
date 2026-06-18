/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { api, db, apiWsUrl } from '../api';
import { SurveyResponse, NationalMetrics, Enumerator } from '../types';
import { INITIAL_SURVEYS, OFFICIAL_COLLECTION_CHANNELS, PINCODE_LOCATIONS } from '../mockData';
import { translations } from '../i18n';
import { TrustBadge, ConfidenceGauge, ReasonPopover } from './TrustComponents';
import { LeafletMap } from './LeafletMap';
import { 
  LayoutDashboard, 
  Radio, 
  TrendingUp, 
  AlertTriangle, 
  Users, 
  BookOpen, 
  Download, 
  HelpCircle, 
  MapPin, 
  ChevronRight, 
  ChevronLeft, 
  RefreshCw, 
  Search, 
  FileText, 
  Clock, 
  ArrowRight, 
  Filter, 
  CheckCircle2, 
  XCircle, 
  Database, 
  Sliders, 
  Calendar, 
  Lock, 
  Check, 
  Wifi, 
  WifiOff, 
  User, 
  ExternalLink, 
  ChevronUp, 
  ChevronDown,
  Sparkles,
  Info
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid, 
  LineChart, 
  Line, 
  AreaChart, 
  Area, 
  Cell
} from 'recharts';

interface SCDWorkspaceProps {
  lang: 'en' | 'hi' | 'ta';
  isColorBlind: boolean;
}

interface LiveIncident {
  id: string;
  enumeratorName: string;
  surveyName: string;
  reason: string;
  confidence: number;
  timestamp: string;
}

interface MapRegion {
  id: string;
  name: string;
  confidence: number;
  responses: number;
  flagRate: number;
  topEnumerators: string[];
}

interface ExportTask {
  id: string;
  filename: string;
  survey: string;
  region: string;
  threshold: number;
  count: number;
  author: string;
  timestamp: string;
  certified: boolean;
}

export const SCDWorkspace: React.FC<SCDWorkspaceProps> = ({ lang, isColorBlind }) => {
  const t = translations[lang];

  // High-level subtabs for the overall command layout
  const [activeSubTab, setActiveSubTab] = useState<'command' | 'search' | 'map' | 'lifecycle' | 'analytics' | 'control' | 'exports'>('command');
  const [semanticQuery, setSemanticQuery] = useState('Tamil Nadu PLFS Income Female Urban 2026');
  const [selectedLifecycleSurveyId, setSelectedLifecycleSurveyId] = useState(INITIAL_SURVEYS[0].id);
  const [selectedLifecycleStage, setSelectedLifecycleStage] = useState(INITIAL_SURVEYS[0].lifecycle?.[0]?.stage || 'Created');

  // Interactive Live websocket simulation states
  const [isWebSocketActive, setIsWebSocketActive] = useState(true);
  const [wsTriggerCount, setWsTriggerCount] = useState(0);

  // States to store db data
  const [metrics, setMetrics] = useState<NationalMetrics>({
    responsesToday: 0,
    flaggedCount: 0,
    avgConfidence: 0,
    activeEnumerators: 0
  });
  
  const [minConfSlider, setMinConfSlider] = useState(40);
  const [incidents, setIncidents] = useState<LiveIncident[]>([
    {
      id: 'resp_1',
      enumeratorName: 'Karthik S. (Suspect profile)',
      surveyName: 'PLFS-2026',
      reason: "Income ₹2,00,000 exceeds ₹10,000 boundary for Unemployed occupation state.",
      confidence: 46,
      timestamp: new Date(Date.now() - 30000).toISOString()
    },
    {
      id: 'resp_2',
      enumeratorName: 'Rajesh G. (High Velocity)',
      surveyName: 'HCES-2026',
      reason: "Answering speed (<3s median per question) points to keyboard straightline script simulation.",
      confidence: 32,
      timestamp: new Date(Date.now() - 120000).toISOString()
    },
    {
      id: 'resp_3',
      enumeratorName: 'Meena K.',
      surveyName: 'PLFS-2026',
      reason: "Geographic coordinate delta: device located 82km away from specified LGD ward.",
      confidence: 58,
      timestamp: new Date(Date.now() - 400000).toISOString()
    }
  ]);

  const [leaderboard, setLeaderboard] = useState<Enumerator[]>([]);
  const [filteredResponses, setFilteredResponses] = useState<SurveyResponse[]>([]);
  const [dbResponses, setDbResponses] = useState<SurveyResponse[]>([]);
  const [successToast, setSuccessToast] = useState('');

  // 9.1 Drilled down read-only response detail sidebar or modal state
  const [drilledResponse, setDrilledResponse] = useState<SurveyResponse | null>(null);

  // 9.2 Geographic state-zoom variables
  const [zoomLevel, setZoomLevel] = useState<'country' | 'state' | 'district'>('country');
  const [selectedState, setSelectedState] = useState<string>('Tamil Nadu');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('Chennai');
  const [pinFilter, setPinFilter] = useState('');
  const [nicFilter, setNicFilter] = useState('ALL');

  const stateOptions = Array.from(new Set(PINCODE_LOCATIONS.map(location => location.state))).sort();
  const districtOptions = Array.from(new Set(
    PINCODE_LOCATIONS
      .filter(location => location.state === selectedState)
      .map(location => location.district)
  )).sort();
  const pincodeOptions = PINCODE_LOCATIONS
    .filter(location => location.state === selectedState && location.district === selectedDistrict)
    .sort((a, b) => a.pincode.localeCompare(b.pincode));
  const selectedLocationScope = PINCODE_LOCATIONS.find(location =>
    location.state === selectedState &&
    location.district === selectedDistrict &&
    (!pinFilter || location.pincode === pinFilter)
  ) || PINCODE_LOCATIONS.find(location => location.state === selectedState && location.district === selectedDistrict);

  // Interactive Live websocket mock trigger
  const triggerMockWebSocketFlag = () => {
    const surveyors = ['Suresh Nair', 'Ketan Mehta', 'Ramya Krishnan', 'Arvinder Singh', 'Amit Sen'];
    const surveys = ['PLFS-2026', 'HCES-2026', 'ASI-2026'];
    const reasons = [
      'Required household census registry index left blank during validation step.',
      'Anomalous rent expense entered (₹95,000) sits outside 99.4th percentile bounds for class.',
      'Multiple back-navigation swaps (x24) detected on high-impact income fields.',
      'Device biometric voice pattern mismatch detected against assigned profile.'
    ];

    const randomSurveyor = surveyors[Math.floor(Math.random() * surveyors.length)];
    const randomSurvey = surveys[Math.floor(Math.random() * surveys.length)];
    const randomReason = reasons[Math.floor(Math.random() * reasons.length)];
    const randomConf = Math.floor(Math.random() * 40) + 25; // 25-65% confidence

    const newAlert: LiveIncident = {
      id: 'resp_ws_' + Date.now().toString().slice(-4),
      enumeratorName: randomSurveyor,
      surveyName: randomSurvey,
      reason: randomReason,
      confidence: randomConf,
      timestamp: new Date().toISOString()
    };

    setIncidents(prev => [newAlert, ...prev].slice(0, 10)); // keep 10 max
    setSuccessToast(`Live feed inflow: critical quality flag dispatched for ${randomSurveyor}.`);
    setWsTriggerCount(c => c + 1);
    setTimeout(() => setSuccessToast(''), 4500);
  };

  const getResponseLocation = (response: SurveyResponse, index: number) => {
    const explicit = response.householdId?.match(/\d{6}/)?.[0];
    const location = explicit
      ? PINCODE_LOCATIONS.find((item) => item.pincode === explicit)
      : PINCODE_LOCATIONS[index % PINCODE_LOCATIONS.length];
    return location || PINCODE_LOCATIONS[0];
  };

  const responseMatchesPincode = (response: SurveyResponse, index: number) => {
    const location = getResponseLocation(response, index);
    if (selectedState && location.state !== selectedState) return false;
    if (selectedDistrict && location.district !== selectedDistrict) return false;
    if (pinFilter.trim() && location.pincode !== pinFilter.trim()) return false;
    return true;
  };

  // 9.2 Mock geographical statistics
  const stateStats: Record<string, MapRegion> = stateOptions.reduce((acc, stateName, index) => {
    const locations = PINCODE_LOCATIONS.filter(location => location.state === stateName);
    const stateResponses = dbResponses.filter((response, responseIndex) => getResponseLocation(response, responseIndex).state === stateName);
    const avgConfidence = stateResponses.length
      ? Math.round(stateResponses.reduce((sum, response) => sum + response.confidenceScore, 0) / stateResponses.length)
      : Math.max(58, Math.min(94, 92 - (index % 9) * 4));
    const flagRate = stateResponses.length
      ? Number(((stateResponses.filter(response => response.trustBand === 'Red').length / stateResponses.length) * 100).toFixed(1))
      : Number((1.1 + (index % 7) * 0.8).toFixed(1));
    acc[stateName] = {
      id: locations[0]?.stateLgdCode || stateName.slice(0, 2).toUpperCase(),
      name: stateName,
      confidence: avgConfidence,
      responses: Math.max(stateResponses.length * 125, locations.length * 425),
      flagRate,
      topEnumerators: leaderboard.filter(enumerator => enumerator.region.includes(stateName)).slice(0, 2).map(enumerator => enumerator.name).concat(['National pool']).slice(0, 2)
    };
    return acc;
  }, {} as Record<string, MapRegion>);

  const districtStatsTN: Record<string, MapRegion> = districtOptions.reduce((acc, districtName, index) => {
    const locations = PINCODE_LOCATIONS.filter(location => location.state === selectedState && location.district === districtName);
    const districtResponses = dbResponses.filter((response, responseIndex) => {
      const location = getResponseLocation(response, responseIndex);
      return location.state === selectedState && location.district === districtName;
    });
    const avgConfidence = districtResponses.length
      ? Math.round(districtResponses.reduce((sum, response) => sum + response.confidenceScore, 0) / districtResponses.length)
      : Math.max(55, Math.min(93, 88 - (index % 6) * 5));
    acc[districtName] = {
      id: locations[0]?.districtLgdCode || `${stateStats[selectedState]?.id || 'LGD'}_${index + 1}`,
      name: districtName,
      confidence: avgConfidence,
      responses: Math.max(districtResponses.length * 125, locations.length * 240),
      flagRate: districtResponses.length
        ? Number(((districtResponses.filter(response => response.trustBand === 'Red').length / districtResponses.length) * 100).toFixed(1))
        : Number((1.4 + (index % 5) * 0.9).toFixed(1)),
      topEnumerators: leaderboard.filter(enumerator => enumerator.region.includes(districtName)).slice(0, 2).map(enumerator => enumerator.name).concat(['District pool']).slice(0, 2)
    };
    return acc;
  }, {} as Record<string, MapRegion>);

  // Live sidebar syncing region info based on drill-down click
  const getCurrentRegionInfo = () => {
    if (zoomLevel === 'state') {
      return stateStats[selectedState] || stateStats['Tamil Nadu'];
    } else if (zoomLevel === 'district') {
      return districtStatsTN[selectedDistrict] || Object.values(districtStatsTN)[0] || stateStats[selectedState];
    }
    // Summary view general India
    return {
      id: 'IND',
      name: 'All India Baseline',
      confidence: 80,
      responses: 33640,
      flagRate: 3.8,
      topEnumerators: ['Lakshmi P.', 'Priya Deshmukh', 'Amit V.']
    };
  };

  const getStatePolygonPoints = (stateName: string) => {
    const pointsByState: Record<string, string> = {
      Rajasthan: '100,105 135,110 145,145 105,155 85,130',
      Gujarat: '65,155 95,155 105,185 80,195 55,175',
      Maharashtra: '95,195 155,195 165,245 125,245 95,225',
      'Uttar Pradesh': '145,115 210,105 225,135 175,155 145,135',
      'West Bengal': '265,145 285,145 295,195 275,205 255,175',
      Odisha: '205,195 245,185 260,235 220,245',
      Karnataka: '105,245 145,245 145,315 115,315',
      'Tamil Nadu': '135,315 175,315 165,385 130,375',
      Kerala: '115,315 135,315 130,375 110,365',
      'Andhra Pradesh': '145,245 195,245 175,315 145,315'
    };
    return pointsByState[stateName] || '';
  };

  const scopedResponseEntries = dbResponses
    .map((response, index) => ({ response, index, location: getResponseLocation(response, index) }))
    .filter(entry => responseMatchesPincode(entry.response, entry.index));
  const scopedResponses = scopedResponseEntries.map(entry => entry.response);

  // 9.3 Custom Exports Builder state management
  const [selectedSurvey, setSelectedSurvey] = useState('PLFS-2026');
  const [selectedExportRegion, setSelectedExportRegion] = useState('Tamil Nadu');
  const [selectedDate, setSelectedDate] = useState('June 2026');
  const [exportThreshold, setExportThreshold] = useState(80);
  const [exportHistory, setExportHistory] = useState<ExportTask[]>([
    {
      id: 'EXP-42',
      filename: 'PLFS_TN_JUNE_CONF80_CLEANSED.csv',
      survey: 'PLFS-2026',
      region: 'Tamil Nadu',
      threshold: 80,
      count: 1204,
      author: 'Amit Verma (Data Governance Administrator)',
      timestamp: '2026-06-09 11:24:02',
      certified: true
    },
    {
      id: 'EXP-41',
      filename: 'HCES_MH_MAY_CONF70_AUDITED.csv',
      survey: 'HCES-2026',
      region: 'Maharashtra',
      threshold: 70,
      count: 2840,
      author: 'Amit Verma (Data Governance Administrator)',
      timestamp: '2026-06-05 16:48:15',
      certified: true
    }
  ]);

  const [generatingExport, setGeneratingExport] = useState(false);

  const csvEscape = (value: any) => {
    if (value === null || value === undefined) return '';
    return `"${String(value).replace(/"/g, '""')}"`;
  };

  const validationStatusFor = (response: SurveyResponse) => {
    const layers = Object.values(response.validation || {});
    if (layers.some(layer => layer.status === 'fail')) return 'Fail';
    if (layers.some(layer => layer.status === 'warn')) return 'Warn';
    return 'Pass';
  };

  const layerStatusFor = (response: SurveyResponse, key: keyof SurveyResponse['validation']) => {
    const layer = response.validation?.[key];
    if (!layer) return 'Pass';
    return `${layer.status.toUpperCase()}: ${layer.reason}`;
  };

  const codedValueFor = (response: SurveyResponse, codeType: 'NIC' | 'NCO') => {
    const values = Object.values(response.codedAnswers || {});
    const byReason = values.find(item => JSON.stringify(item).toUpperCase().includes(codeType));
    if (byReason?.code && byReason.code !== 'None') return byReason.code;
    if (codeType === 'NIC') return response.nicCode || '';
    if (codeType === 'NCO') return response.occupation ? response.occupation : '';
    return '';
  };

  const nationalReportHeaders = [
    'Response_ID',
    'Survey_ID',
    'Survey_Name',
    'State',
    'District',
    'Pincode',
    'Enumerator_ID',
    'Interview_Date',
    'Start_Time',
    'End_Time',
    'Duration_Minutes',
    'Latitude',
    'Longitude',
    'GPS_Accuracy',
    'Device_ID',
    'Language',
    'Trust_Score',
    'Validation_Status',
    'Structural_Check',
    'Logic_Check',
    'Statistical_Check',
    'Semantic_Check',
    'Historical_Check',
    'Flag_Count',
    'Flag_Type',
    'Quality_Status',
    'NIC_Code',
    'NCO_Code',
    'Export_Status',
    'Created_At'
  ];

  const buildNationalReportRows = () => {
    const qualifyingEntries = scopedResponseEntries
      .filter(({ response }) => response.confidenceScore >= exportThreshold)
      .filter(({ response }) => selectedSurvey === 'PLFS-2026' || response.surveyName.toLowerCase().includes(selectedSurvey.slice(0, 4).toLowerCase()));

    const entries = qualifyingEntries.length ? qualifyingEntries : scopedResponseEntries;
    return entries.map(({ response, index, location }) => {
      const timestamp = new Date(response.timestamp);
      const totalMs = Object.values(response.paradata.timePerQuestion || {}).reduce((sum, value) => sum + Number(value || 0), 0);
      const durationMinutes = Math.max(1, Math.round((totalMs / 60000) * 10) / 10);
      const endTime = Number.isNaN(timestamp.getTime()) ? new Date() : timestamp;
      const startTime = new Date(endTime.getTime() - durationMinutes * 60000);
      const flagTypes = response.flaggedBy?.length
        ? response.flaggedBy.join('|')
        : Object.entries(response.validation || {})
          .filter(([, layer]) => layer.status !== 'pass')
          .map(([key]) => key)
          .join('|');

      return {
        Response_ID: response.id,
        Survey_ID: response.surveyId,
        Survey_Name: response.surveyName,
        State: location.state,
        District: location.district,
        Pincode: location.pincode,
        Enumerator_ID: response.enumeratorId,
        Interview_Date: endTime.toISOString().slice(0, 10),
        Start_Time: startTime.toISOString(),
        End_Time: endTime.toISOString(),
        Duration_Minutes: durationMinutes,
        Latitude: response.paradata.gpsLat || location.lat,
        Longitude: response.paradata.gpsLng || location.lng,
        GPS_Accuracy: index % 3 === 0 ? '8m' : index % 3 === 1 ? '12m' : '18m',
        Device_ID: `SATARK-${response.paradata.mode || 'CAPI'}-${response.enumeratorId}`,
        Language: typeof response.answers?.language === 'string' ? response.answers.language : 'en',
        Trust_Score: response.confidenceScore,
        Validation_Status: validationStatusFor(response),
        Structural_Check: layerStatusFor(response, 'layer1_rule'),
        Logic_Check: layerStatusFor(response, 'layer5_cross'),
        Statistical_Check: layerStatusFor(response, 'layer3_bayesian'),
        Semantic_Check: layerStatusFor(response, 'layer2_govt'),
        Historical_Check: layerStatusFor(response, 'layer4_behavior'),
        Flag_Count: response.flaggedBy?.length || Object.values(response.validation || {}).filter(layer => layer.status !== 'pass').length,
        Flag_Type: flagTypes || 'None',
        Quality_Status: response.status,
        NIC_Code: codedValueFor(response, 'NIC'),
        NCO_Code: codedValueFor(response, 'NCO'),
        Export_Status: 'Ready',
        Created_At: response.timestamp
      };
    });
  };

  const downloadNationalReportCSV = (filename: string) => {
    const rows = buildNationalReportRows();
    const csv = [
      nationalReportHeaders.join(','),
      ...rows.map(row => nationalReportHeaders.map(header => csvEscape((row as Record<string, any>)[header])).join(','))
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    return rows.length;
  };

  const handleGenerateExport = () => {
    setGeneratingExport(true);
    setTimeout(() => {
      const fileCode = selectedSurvey.slice(0,4) + '_' + selectedExportRegion.replace(' ', '').toUpperCase().slice(0,3) + '_' + Date.now().toString().slice(-4);
      const filename = `${fileCode}_CONF${exportThreshold}_COMPLETE_REPORT.csv`;
      const computedCount = downloadNationalReportCSV(filename);
      const newTask: ExportTask = {
        id: 'EXP-' + (exportHistory.length + 41),
        filename,
        survey: selectedSurvey,
        region: selectedExportRegion,
        threshold: exportThreshold,
        count: computedCount,
        author: 'Amit Verma (Data Governance Administrator)',
        timestamp: new Date().toISOString().replace('T', ' ').slice(0, 19),
        certified: true
      };
      setExportHistory(prev => [newTask, ...prev]);
      setGeneratingExport(false);
      setSuccessToast(`Complete national report downloaded with ${computedCount} real response/paradata row(s).`);
      setTimeout(() => setSuccessToast(''), 4000);
    }, 1500);
  };

  // Load from local model APIs
  useEffect(() => {
    loadSCDData();

    if (!isWebSocketActive) return;

    const token = localStorage.getItem('satark_token') || '';
    // Access websocket via api routing proxy path (or VITE_API_URL tunnel in prod)
    const wsUrl = apiWsUrl('/events/live', token);

    console.log("Connecting to WebSocket:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connected to SATARK event stream");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        console.log("WebSocket message received:", payload);
        
        if (payload.event === 'connected') {
          return;
        }

        // Trigger reload of SCD data whenever an event is dispatched
        loadSCDData();

        // If the event represents a flag or low trust response, add to the incident dashboard
        if (payload.risk_level === 'Red' || payload.event === 'flag.created') {
          const reasonText = payload.reasons && payload.reasons.length > 0
            ? payload.reasons.join(", ")
            : "Critical validation flags failed.";
          
          const newAlert: LiveIncident = {
            id: payload.response_id || 'resp_ws_' + Date.now().toString().slice(-4),
            enumeratorName: payload.enumerator_id || 'Unknown Surveyor',
            surveyName: 'PLFS-2026',
            reason: reasonText,
            confidence: payload.confidence || 40,
            timestamp: new Date().toISOString()
          };

          setIncidents(prev => {
            if (prev.some(x => x.id === newAlert.id)) return prev;
            return [newAlert, ...prev].slice(0, 10);
          });

          setSuccessToast(`Live feed: critical quality flag dispatched for ${payload.enumerator_id || 'Surveyor'}.`);
          setTimeout(() => setSuccessToast(''), 4500);
        }
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    ws.onerror = (err) => {
      console.warn("WebSocket connection error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
    };

    return () => {
      ws.close();
    };
  }, [isWebSocketActive, minConfSlider]);

  useEffect(() => {
    const districts = Array.from(new Set(
      PINCODE_LOCATIONS
        .filter(location => location.state === selectedState)
        .map(location => location.district)
    )).sort();
    if (districts.length > 0 && !districts.includes(selectedDistrict)) {
      setSelectedDistrict(districts[0]);
      setPinFilter('');
    }
  }, [selectedState, selectedDistrict]);

  useEffect(() => {
    if (!pinFilter) return;
    const isValidPin = PINCODE_LOCATIONS.some(location =>
      location.state === selectedState &&
      location.district === selectedDistrict &&
      location.pincode === pinFilter
    );
    if (!isValidPin) setPinFilter('');
  }, [selectedState, selectedDistrict, pinFilter]);

  const loadSCDData = async () => {
    // Re-verify responses against slider logic
    const res = await api.getNationalMetrics(minConfSlider);
    setMetrics({
      responsesToday: res.responsesToday,
      flaggedCount: res.flaggedCount,
      avgConfidence: res.avgConfidence,
      activeEnumerators: res.activeEnumerators
    });
    setFilteredResponses(res.filteredResponses);

    const raw = await api.getResponses();
    setDbResponses(raw);

    const enums = await api.getEnumerators();
    setLeaderboard(enums);
  };

  const forceWSReconnect = () => {
    setIsWebSocketActive(true);
    setSuccessToast('Real-time event feed established successfully.');
    setTimeout(() => setSuccessToast(''), 3000);
  };

  // Computations for 9.1 sliding limits recomputes
  // Let's emulate 1204 responses total scaling factor for realistic high-volume displays
  const scaleRatio = 12.5; 
  const totalSimulated = Math.round(dbResponses.length * scaleRatio);
  const includedSimulated = Math.round(filteredResponses.length * scaleRatio);
  const excludedSimulated = Math.max(0, totalSimulated - includedSimulated);

  // 9.3 CSV charts download helper
  const handleDownloadChartCSV = (chartTitle: string, payload: any[]) => {
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "Label,Count/Value\n";
    payload.forEach(row => {
      csvContent += `"${row.name || row.range || row.name_en || row.id}","${row.count || row.TrustScore || row.confidenceScore || 0}"\n`;
    });
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `SATARK_Export_${chartTitle.replace(' ', '_')}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setSuccessToast(`CSV dataset exported for: ${chartTitle}`);
    setTimeout(() => setSuccessToast(''), 3500);
  };

  return (
    <div className="space-y-6 text-left" id="scd-workspace-main">
      
      {/* SVG Pattern Definitions for color-blind accessibilities */}
      <svg className="hidden" aria-hidden="true">
        <defs>
          <pattern id="diagonal-stripes-red" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="8" stroke="#ef4444" strokeWidth="2.5" />
            <rect width="8" height="8" fill="#fef2f2" className="opacity-40" />
          </pattern>
          <pattern id="cross-stripes-amber" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(135)">
            <line x1="0" y1="0" x2="0" y2="10" stroke="#f59e0b" strokeWidth="2" />
            <rect width="10" height="10" fill="#fffbeb" className="opacity-40" />
          </pattern>
          <pattern id="dotted-matrix-green" width="6" height="6" patternUnits="userSpaceOnUse">
            <circle cx="3" cy="3" r="1.5" fill="#10b981" />
            <rect width="6" height="6" fill="#f0fdf4" className="opacity-40" />
          </pattern>
        </defs>
      </svg>

      {/* Global GoI Style Header */}
      <header className="bg-white p-5 rounded-2xl border border-slate-150 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-150 flex items-center justify-center font-black text-indigo-700 shadow-inner">
              <LayoutDashboard className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h1 className="text-lg font-black text-slate-950 tracking-tight flex items-center gap-1.5">
                {t.scd_command_title}
              </h1>
              <p className="text-[11px] text-slate-500 font-medium">National survey assurance live terminal & high-volume policy filtering</p>
            </div>
          </div>
        </div>

        {/* Global tab controllers */}
        <div className="flex bg-slate-100 border border-slate-200 p-1 rounded-xl gap-1.5 text-xs font-bold w-full md:w-auto">
          <button
            onClick={() => setActiveSubTab('command')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'command' 
                ? 'bg-indigo-950 text-white shadow-md' 
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Live Command Feed
          </button>
          <button
            onClick={() => setActiveSubTab('search')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'search'
                ? 'bg-indigo-950 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            National Search
          </button>
          <button
            onClick={() => setActiveSubTab('map')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'map' 
                ? 'bg-indigo-950 text-white shadow-md' 
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Geographic Coverage Map
          </button>
          <button
            onClick={() => setActiveSubTab('lifecycle')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'lifecycle'
                ? 'bg-indigo-950 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Lifecycle
          </button>
          <button
            onClick={() => setActiveSubTab('analytics')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'analytics' 
                ? 'bg-indigo-950 text-white shadow-md' 
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Trust Analytics
          </button>
          <button
            onClick={() => setActiveSubTab('control')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'control'
                ? 'bg-indigo-950 text-white shadow-md'
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Master Control
          </button>
          <button
            onClick={() => setActiveSubTab('exports')}
            className={`flex-1 md:flex-initial px-4 py-2 rounded-lg text-center font-bold tracking-tight text-[10px] uppercase transition-all whitespace-nowrap ${
              activeSubTab === 'exports' 
                ? 'bg-indigo-950 text-white shadow-md' 
                : 'text-slate-600 hover:text-slate-950 hover:bg-slate-50'
            }`}
          >
            Cleansed Data Exports
          </button>
        </div>
      </header>

      {/* Toast Notification Alert Area (Green UI Banner) */}
      {successToast && (
        <div className="p-4 bg-emerald-50 border-2 border-emerald-250 text-emerald-900 rounded-xl text-xs font-bold flex items-center justify-between shadow-sm animate-slideDown">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4.5 h-4.5 text-emerald-600 shrink-0" />
            <span>{successToast}</span>
          </div>
          <button onClick={() => setSuccessToast('')} className="text-emerald-700 hover:text-emerald-900 font-bold font-mono">×</button>
        </div>
      )}

      {/* ======================================================== */}
      {/* KPI METRICS HEADER ROW */}
      {/* ======================================================== */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* KPI 1 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden text-left">
          <div className="flex items-center justify-between pb-1">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t.metricsResponses}</span>
            <Database className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight gap-1.5 flex items-baseline">
            {metrics.responsesToday}
            <span className="text-[10px] text-emerald-600 font-bold font-sans animate-pulse">● Live</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1 font-medium">Live telemetry streaming from 32 field regions</p>
        </div>

        {/* KPI 2 */}
        <div className={`p-5 rounded-2xl border shadow-sm relative transition-all text-left ${
          metrics.flaggedCount > 0 ? 'bg-rose-50/70 border-rose-220 text-rose-950' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center justify-between pb-1">
            <span className={`text-[10px] font-black uppercase tracking-widest ${
              metrics.flaggedCount > 0 ? 'text-rose-700' : 'text-slate-400'
            }`}>{t.metricsFlagged}</span>
            <AlertTriangle className={`w-4 h-4 ${metrics.flaggedCount > 0 ? 'text-rose-600 animate-bounce' : 'text-slate-400'}`} />
          </div>
          <div className="text-3xl font-extrabold font-mono tracking-tight">{metrics.flaggedCount}</div>
          <p className="text-[10px] text-slate-500 mt-1 font-medium">Critical anomalies routed to validation queues</p>
          {metrics.flaggedCount > 0 && (
            <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-rose-500 animate-ping" />
          )}
        </div>

        {/* KPI 3 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-left">
          <div className="flex items-center justify-between pb-1">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t.metricsAvgConfidence}</span>
            <TrendingUp className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">{metrics.avgConfidence}%</div>
          <p className="text-[10px] text-slate-500 mt-1 font-medium">National weighted safety score average</p>
        </div>

        {/* KPI 4 */}
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-left">
          <div className="flex items-center justify-between pb-1">
            <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t.metricsActive}</span>
            <Users className="w-4 h-4 text-indigo-600" />
          </div>
          <div className="text-3xl font-extrabold text-slate-950 font-mono tracking-tight">244</div>
          <p className="text-[10px] text-slate-500 mt-1 font-medium">Device sessions reporting active today</p>
        </div>

      </section>

      <section className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-3">
        {[
          ['Total Surveys', INITIAL_SURVEYS.length],
          ['Active Surveys', INITIAL_SURVEYS.filter(s => s.status === 'Published').length],
          ['Completed Interviews', '1,24,000'],
          ['Coverage', '92%'],
          ['Trust', `${metrics.avgConfidence || 96}%`],
          ['Enumerators', leaderboard.length || 10],
          ['Districts Covered', 38],
          ['Quality Score', '96%']
        ].map(([label, value]) => (
          <div key={label} className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm">
            <span className="text-[9px] font-black uppercase tracking-wider text-slate-400 block">{label}</span>
            <strong className="text-lg font-black text-slate-900 font-mono">{value}</strong>
          </div>
        ))}
      </section>

      {/* ======================================================== */}
      {/* NATIONAL SEMANTIC SEARCH */}
      {/* ======================================================== */}
      {activeSubTab === 'search' && (
        <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-5">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div>
              <h2 className="font-black text-sm uppercase text-slate-900">National Search</h2>
              <p className="text-[11px] text-slate-500 mt-0.5">Search responses, analytics, reports, raw data, and survey metadata from one control point.</p>
            </div>
            <div className="relative w-full lg:w-[420px]">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={semanticQuery}
                onChange={e => setSemanticQuery(e.target.value)}
                placeholder="Tamil Nadu PLFS Income Female Urban 2026"
                className="w-full p-3 pl-9 border border-slate-200 rounded-xl text-xs font-bold bg-slate-50 focus:outline-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-8 gap-2 text-[10px] font-bold">
            <select
              value={selectedState}
              onChange={event => {
                setSelectedState(event.target.value);
                setZoomLevel('state');
              }}
              className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700"
            >
              {stateOptions.map(state => <option key={state} value={state}>{state}</option>)}
            </select>
            <select
              value={selectedDistrict}
              onChange={event => {
                setSelectedDistrict(event.target.value);
                setPinFilter('');
                setZoomLevel('district');
              }}
              className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700"
            >
              {districtOptions.map(district => <option key={district} value={district}>{district}</option>)}
            </select>
            <select
              value={pinFilter}
              onChange={event => setPinFilter(event.target.value)}
              className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700"
            >
              <option value="">All pincodes</option>
              {pincodeOptions.map(location => (
                <option key={location.pincode} value={location.pincode}>{location.pincode} - {location.locality}</option>
              ))}
            </select>
            <select value={selectedSurvey} onChange={event => setSelectedSurvey(event.target.value)} className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
              {['PLFS-2026', 'HCES-2026', 'ASUSE-2026', 'AGRI-2026'].map(survey => <option key={survey}>{survey}</option>)}
            </select>
            <select className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
              <option>All questions</option>
              <option>Employment</option>
              <option>Income</option>
              <option>Household</option>
            </select>
            <select className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
              <option>All languages</option>
              <option>English</option>
              <option>Hindi</option>
              <option>Tamil</option>
            </select>
            <select value={exportThreshold} onChange={event => setExportThreshold(Number(event.target.value))} className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
              {[40, 60, 70, 80, 90].map(value => <option key={value} value={value}>Trust &gt;= {value}%</option>)}
            </select>
            <select value={selectedDate} onChange={event => setSelectedDate(event.target.value)} className="p-2 border border-slate-200 rounded-lg bg-slate-50 text-slate-700">
              {['June 2026', 'May 2026', 'April 2026', 'Q1 2026'].map(value => <option key={value}>{value}</option>)}
            </select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {[
              ['Responses', scopedResponses.length || getCurrentRegionInfo().responses, 'Matching answer records and paradata.'],
              ['Analytics', 8, 'Coverage and quality rollups.'],
              ['Reports', 5, 'Published and draft report packs.'],
              ['Raw Data', Math.max(1200, getCurrentRegionInfo().responses * 2).toLocaleString('en-IN'), 'Cleaned rows available for export.'],
              ['Survey Metadata', INITIAL_SURVEYS.length, 'DDI IDs, lifecycle, and source trace.']
            ].map(([title, value, body]) => (
              <div key={title} className="p-4 bg-slate-50 border border-slate-200 rounded-xl">
                <span className="text-[10px] font-black uppercase text-slate-400">{title}</span>
                <div className="text-2xl font-black text-slate-900 font-mono">{value}</div>
                <p className="text-[10px] text-slate-500 mt-1">{body}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ======================================================== */}
      {/* SURVEY LIFECYCLE MIND MAP */}
      {/* ======================================================== */}
      {activeSubTab === 'lifecycle' && (() => {
        const survey = INITIAL_SURVEYS.find(s => s.id === selectedLifecycleSurveyId) || INITIAL_SURVEYS[0];
        const stages = survey.lifecycle || [];
        const selectedStage = stages.find(stage => stage.stage === selectedLifecycleStage) || stages[0];
        return (
          <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h2 className="font-black text-sm uppercase text-slate-900">Survey Lifecycle Mind Map</h2>
                <p className="text-[11px] text-slate-500 mt-0.5">Every survey stage shows records, issues, trust, validation logs, and audit trail.</p>
              </div>
              <select value={selectedLifecycleSurveyId} onChange={e => setSelectedLifecycleSurveyId(e.target.value)} className="p-2 border border-slate-200 rounded-lg text-xs font-bold bg-slate-50">
                {INITIAL_SURVEYS.map(s => <option key={s.id} value={s.id}>{s.shortName || s.name_en}</option>)}
              </select>
            </div>

            <div className="overflow-x-auto">
              <div className="flex gap-3 min-w-max">
                {stages.map((stage) => (
                  <button
                    key={stage.stage}
                    onClick={() => setSelectedLifecycleStage(stage.stage)}
                    className={`min-w-[150px] p-3 rounded-xl border text-left transition ${
                      selectedLifecycleStage === stage.stage ? 'bg-indigo-950 text-white border-indigo-950' : 'bg-slate-50 border-slate-200 text-slate-700 hover:border-indigo-300'
                    }`}
                  >
                    <span className="text-[9px] uppercase font-black opacity-70">{stage.status}</span>
                    <strong className="block text-sm">{stage.stage}</strong>
                    <span className="text-[10px] opacity-80">{stage.records}</span>
                  </button>
                ))}
              </div>
            </div>

            {selectedStage && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50"><span className="text-[10px] uppercase font-black text-slate-400">Records</span><strong className="block text-slate-900">{selectedStage.records}</strong></div>
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50"><span className="text-[10px] uppercase font-black text-slate-400">Issues</span><strong className="block text-slate-900">{selectedStage.issues}</strong></div>
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50"><span className="text-[10px] uppercase font-black text-slate-400">Trust</span><strong className="block text-slate-900">{selectedStage.trust}%</strong></div>
                <div className="p-4 rounded-xl border border-slate-200 bg-slate-50"><span className="text-[10px] uppercase font-black text-slate-400">Audit Trail</span><p className="text-[11px] text-slate-600 font-semibold">{selectedStage.audit}</p></div>
              </div>
            )}
          </section>
        );
      })()}

      {/* ======================================================== */}
      {/* MASTER CONTROL PANEL */}
      {/* ======================================================== */}
      {activeSubTab === 'control' && (
        <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-5">
          <div>
            <h2 className="font-black text-sm uppercase text-slate-900">Unified National Intelligence Control Center</h2>
            <p className="text-[11px] text-slate-500 mt-0.5">Single command point for design, field, processing, channels, exports, and analytics.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {['Survey Design', 'Field Operation', 'C&QCD', 'Voice Surveys', 'WhatsApp Surveys', 'Web Surveys', 'Mobile App Surveys', 'Exports', 'Analytics'].map((item) => (
              <button key={item} className="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:border-indigo-300 text-left">
                <span className="text-[10px] font-black uppercase text-slate-400">Control</span>
                <strong className="block text-sm text-slate-900">{item}</strong>
                <span className="text-[10px] text-emerald-700 font-bold">Operational</span>
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
            {OFFICIAL_COLLECTION_CHANNELS.map((channel) => (
              <div key={channel.id} className="p-3 rounded-xl bg-emerald-50 border border-emerald-100">
                <span className="text-[9px] font-black uppercase text-emerald-700">{channel.status}</span>
                <strong className="block text-xs text-emerald-950">{channel.label}</strong>
                <p className="text-[10px] text-emerald-800">{channel.sessionsToday} sessions today</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ======================================================== */}
      {/* SECTION 9.1: LIVE COMMAND FEED & LEADERBOARD MAIN TAB */}
      {/* ======================================================== */}
      {activeSubTab === 'command' && (
        <div className="space-y-6">
          
          {/* Row 2 split: Left flag feed 55%, Right trust leaderboard 45% */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Live Flag feed panel (55% width) */}
            <div className="lg:col-span-7 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
              
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-slate-100">
                <div>
                  <h3 className="font-extrabold text-sm text-slate-900 tracking-tight flex items-center gap-1.5 uppercase">
                    <Radio className="w-4.5 h-4.5 text-emerald-500 animate-pulse" />
                    Live Quality Flag Feed
                  </h3>
                  <p className="text-[10px] text-slate-500 italic mt-0.5">Continuous validation telemetry from national database stream</p>
                </div>

                {/* Websocket system indicators & controllers */}
                <div className="flex items-center gap-1.5">
                  {!isWebSocketActive ? (
                    <button 
                      onClick={forceWSReconnect}
                      className="px-2.5 py-1 bg-amber-500/10 border border-amber-300 text-amber-700 text-[10px] rounded-lg font-black animate-pulse flex items-center gap-1"
                    >
                      <WifiOff className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                      Reconnecting — polling every 3s
                    </button>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-800 border border-emerald-250 px-2 py-0.5 rounded text-[9px] font-black uppercase">
                        <Wifi className="w-3 h-3 text-emerald-600" /> Live Feed Connected
                      </span>
                      <button 
                        onClick={() => triggerMockWebSocketFlag()}
                        className="p-1 text-slate-500 hover:text-indigo-800 hover:bg-slate-50 rounded-lg text-[9px] border font-bold flex items-center gap-1"
                        title="Force sample incident event ingestion"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-500 animate-spin" /> Ingest Flag
                      </button>
                    </div>
                  )}

                  {/* Controller toggle */}
                  <button
                    onClick={() => setIsWebSocketActive(!isWebSocketActive)}
                    className="p-1 border border-slate-205 rounded hover:bg-slate-50 font-bold text-[9px]"
                    title="Toggle simulated client socket connection status"
                  >
                    {isWebSocketActive ? "Pause Feed" : "Start Feed"}
                  </button>
                </div>
              </div>

              {/* Incidents feed stack */}
              <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
                {incidents.map((inc, index) => (
                  <div
                    key={inc.id + index}
                    onClick={() => {
                      // Lookup database response to load DPD drilldown modal format
                      const foundResp = dbResponses.find(r => r.id === inc.id) || dbResponses[0];
                      setDrilledResponse(foundResp);
                    }}
                    className={`p-3 bg-slate-50/60 hover:bg-indigo-50/15 border border-slate-200 hover:border-indigo-900 rounded-xl cursor-pointer text-xs flex gap-3 items-start transition-all animate-fadeIn ${
                      index === 0 ? 'border-l-4 border-l-rose-500' : ''
                    }`}
                  >
                    <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shrink-0 mt-1.5 animate-pulse" />
                    
                    <div className="space-y-1.5 flex-1">
                      <div className="flex justify-between items-start gap-4">
                        <span className="font-black text-slate-800">
                          {inc.enumeratorName}
                        </span>
                        <div className="flex items-center gap-1.5 text-[9px] font-bold text-slate-400 font-mono">
                          <Clock className="w-3 h-3 text-slate-400" />
                          {index === 0 ? 'Just now' : index === 1 ? '2 mins ago' : '5 mins ago'}
                        </div>
                      </div>

                      <p className="text-slate-600 leading-relaxed font-medium">"{inc.reason}"</p>
                      
                      <div className="flex justify-between items-center text-[10px] border-t border-slate-100/80 pt-1.5 mt-1 font-semibold">
                        <div className="flex items-center gap-2">
                          <span className="bg-slate-100 border border-slate-150 py-0.5 px-2 rounded-full font-mono text-[9px]">
                            {inc.surveyName}
                          </span>
                          <span className="text-slate-300">•</span>
                          <span className="text-slate-500 font-mono text-[9px]">ID: #{inc.id}</span>
                        </div>

                        {/* ReasonPopover triggers custom popup */}
                        <ReasonPopover 
                          reason={inc.reason} 
                          ruleSource={`${inc.surveyName}-QUALITY-Z2`} 
                          timestamp={inc.timestamp}
                        >
                          <span className={`px-2 py-0.5 rounded font-black uppercase text-[9px] ${
                            inc.confidence >= 80 ? 'bg-emerald-50 text-emerald-800' :
                            inc.confidence >= 50 ? 'bg-amber-50 text-amber-800' : 'bg-rose-50 text-rose-800 animate-pulse'
                          }`}>
                            Quality: {inc.confidence}%
                          </span>
                        </ReasonPopover>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-slate-100/50 p-2 text-center rounded-lg text-[10.5px] text-slate-500 font-medium italic">
                * Click any card row above to deploy the read-only C&QCD drilldown validation console.
              </div>
            </div>

            {/* Enumerator Trust Leaderboard (45% width) */}
            <div className="lg:col-span-5 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900 tracking-tight uppercase">
                  Enumerator Trust Leaderboard
                </h3>
                <p className="text-[10px] text-slate-500 mt-0.5">Regional active enumerators. Bottom-5 marked with fabrication warnings</p>
              </div>

              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {leaderboard.map((enumItem, idx) => {
                  // Pre-program bottom list identifiers for testing
                  const isBottomFive = enumItem.trustScore < 70; 

                  return (
                    <div 
                      key={enumItem.id}
                      className={`p-2.5 rounded-xl border flex justify-between items-center text-xs transition-all ${
                        isBottomFive 
                          ? 'bg-rose-50/45 border-rose-200/60 shadow-inner' 
                          : 'bg-white border-slate-150'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className={`w-5 h-5 font-mono text-[10px] font-black rounded-full flex items-center justify-center ${
                          idx < 3 ? 'bg-indigo-950 text-white' : 'bg-slate-100 text-slate-600'
                        }`}>
                          #{idx + 1}
                        </span>
                        
                        <div>
                          <div className="font-bold text-slate-900 flex items-center gap-1.5">
                            {enumItem.name}
                            {isBottomFive && (
                              <span className="bg-rose-200 text-rose-800 text-[8px] font-black uppercase px-1 rounded animate-pulse">
                                Auditing
                              </span>
                            )}
                          </div>
                          <div className="text-[10px] text-slate-400 font-semibold">{enumItem.region}</div>
                        </div>
                      </div>

                      {/* Sparkline visualization column */}
                      <div className="w-16 h-8 text-right font-medium">
                        <svg className="w-full h-full stroke-indigo-650 stroke-2 fill-none" viewBox="0 0 50 20">
                          <polyline 
                            points={enumItem.sparkline.map((val, key) => `${(key / 6) * 45 + 2.5},${20 - (val / 100) * 16 - 2}`).join(' ')} 
                            stroke={isBottomFive ? '#f43f5e' : '#4f46e5'}
                          />
                        </svg>
                      </div>

                      <div className="text-right">
                        <TrustBadge 
                          score={enumItem.trustScore} 
                          band={enumItem.trustScore >= 80 ? 'Green' : enumItem.trustScore >= 50 ? 'Amber' : 'Red'} 
                          isColorBlind={isColorBlind} 
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="text-right text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                Total surveyed: 24 active sessions in progress
              </div>
            </div>

          </section>

          {/* Row 3: Live GIS mapping + Slider aggregates integration */}
          <section className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 text-left">
            
            {/* Slider aggregations control */}
            <div className="p-4 bg-indigo-950/5 border border-indigo-200/50 rounded-xl space-y-3.5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-indigo-100/50 pb-2.5">
                <div>
                  <h4 className="text-xs font-black text-indigo-950 uppercase tracking-wider">National Trust Filtering Threshold</h4>
                  <p className="text-[10px] text-slate-500 font-semibold italic mt-0.5">Instantly adjust minimum acceptable confidence limits for state aggregates</p>
                </div>
                
                {/* Dynamically recalculated aggregate stats */}
                <span className="bg-indigo-950 text-white font-mono text-[11px] font-black px-3 py-1.5 rounded-lg shadow-sm">
                  At &gt;= {minConfSlider}% Quality: {includedSimulated} included / {excludedSimulated} excluded
                </span>
              </div>

              <div className="flex items-center gap-4">
                <span className="font-mono text-xs text-slate-400">0%</span>
                <input 
                  type="range"
                  min="0"
                  max="100"
                  value={minConfSlider}
                  onChange={e => setMinConfSlider(Number(e.target.value))}
                  className="flex-1 accent-indigo-950 cursor-ew-resize h-2 bg-slate-200 rounded-lg appearance-none"
                />
                <span className="font-mono text-xs text-slate-400">100%</span>
                
                <div className="bg-white border border-slate-250 py-1.5 px-3 rounded-lg text-xs font-mono font-black shadow-sm shrink-0">
                  Cutoff Limit: {minConfSlider}%
                </div>
              </div>

              <p className="text-[10.5px] text-slate-500 font-semibold italic">
                Caption constraint: <strong className="text-slate-800">"Untrusted data excluded by construction."</strong>
              </p>
            </div>

            {/* Quick interactive shortcut mapping preview */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5 pt-3 items-center">
              
              <div className="md:col-span-8 p-3 bg-slate-50 rounded-xl border flex flex-col justify-between relative overflow-hidden animate-fadeIn" style={{ minHeight: '280px' }}>
                <div className="z-10 text-[10px] bg-slate-900 text-white px-2 py-0.5 rounded font-bold font-mono self-start border flex items-center gap-1.5 mb-2">
                  <span className="p-1 w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" />
                  National GIS coordinate plot coordinates
                </div>

                <div className="w-full relative h-[180px] mb-2">
                  <LeafletMap 
                    center={[13.0827, 80.2707]} 
                    zoom={11} 
                    height="180px"
                    markers={filteredResponses.slice(0, 15).map((gps, idx) => {
                      const location = getResponseLocation(gps, idx);
                      return {
                      id: gps.id || `home-${idx}`,
                      lat: gps.paradata.gpsLat || location.lat,
                      lng: gps.paradata.gpsLng || location.lng,
                      title: `Household ${gps.householdId || gps.id}`,
                      subtitle: `PIN ${location.pincode}, ${location.locality} | Occupation: ${gps.occupation || 'Not coded'}`,
                      badge: gps.trustBand === 'Red' ? '⚠ Quality Warning' : '✓ Verified Secure',
                      badgeColor: gps.trustBand === 'Red' ? '#E24B4A' : '#1D9E75'
                    };
                    })}
                    onMarkerClick={(id) => {
                      const found = dbResponses.find(r => r.id === id);
                      if (found) setDrilledResponse(found);
                    }}
                  />
                </div>

                <div className="z-10 flex justify-between items-center text-[10.5px] text-slate-500 font-mono font-bold">
                  <span>Tamil Nadu Stratum Zone bounds: 13.08° N / 80.27° E</span>
                  <button 
                    onClick={() => setActiveSubTab('map')}
                    className="text-xs text-[#14387F] hover:underline font-bold flex items-center gap-1"
                  >
                    Load GIS Map view <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="md:col-span-4 p-4 bg-white border border-slate-205 rounded-xl space-y-3">
                <span className="text-[9px] font-black text-rose-600 tracking-wider uppercase block">Anomalous Outlier Coordinates</span>
                
                <div className="space-y-2 text-[11px]">
                  <div className="p-2 bg-rose-50/50 border border-thin border-rose-150 rounded flex justify-between justify-items-center">
                    <span className="font-bold text-rose-900 font-mono">HH-TN-43-A1</span>
                    <span className="text-slate-500">Mismatched LGD cell ID (Red)</span>
                  </div>
                  <div className="p-2 bg-rose-50/50 border border-thin border-rose-150 rounded flex justify-between justify-items-center">
                    <span className="font-bold text-rose-900 font-mono">HH-TN-44-C3</span>
                    <span className="text-slate-500">Speeding straight-line alert</span>
                  </div>
                </div>

                <p className="text-[10px] text-slate-400 italic">
                  * GIS telemetry is stored cryptographically to comply with regional and National GoI security standards.
                </p>
              </div>

            </div>

          </section>

        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 9.2: INTERACTIVE GEOGRAPHIC COVERAGE ZOOM MAP */}
      {/* ======================================================== */}
      {activeSubTab === 'map' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start" id="map-workspace-tab">
          
          {/* Main Map Box & filters (65% width) */}
          <div className="lg:col-span-8 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4">
            
            {/* Map Filters bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 p-3 rounded-xl border border-slate-150">
              <div className="flex flex-wrap items-center gap-3">

                <select
                  value={selectedState}
                  onChange={event => {
                    setSelectedState(event.target.value);
                    setZoomLevel('state');
                    setPinFilter('');
                  }}
                  className="p-1.5 border border-slate-205 rounded-lg text-[11px] font-bold bg-white focus:outline-indigo-500"
                >
                  {stateOptions.map(state => <option key={state} value={state}>{state}</option>)}
                </select>

                <select
                  value={selectedDistrict}
                  onChange={event => {
                    setSelectedDistrict(event.target.value);
                    setZoomLevel('district');
                    setPinFilter('');
                  }}
                  className="p-1.5 border border-slate-205 rounded-lg text-[11px] font-bold bg-white focus:outline-indigo-500"
                >
                  {districtOptions.map(district => <option key={district} value={district}>{district}</option>)}
                </select>

                <div className="text-xs">
                  <select
                    value={pinFilter}
                    onChange={e => {
                      setPinFilter(e.target.value);
                      setZoomLevel('district');
                    }}
                    className="p-1.5 border border-slate-205 rounded-lg text-[11px] font-bold focus:outline-indigo-500 bg-white"
                  >
                    <option value="">All pincodes</option>
                    {pincodeOptions.map(location => (
                      <option key={location.pincode} value={location.pincode}>{location.pincode} - {location.locality}</option>
                    ))}
                  </select>
                </div>

                {/* Industry filtering uses NIC descriptions */}
                <div className="text-xs">
                  <select
                    value={nicFilter}
                    onChange={e => setNicFilter(e.target.value)}
                    className="p-1.5 border border-slate-205 rounded-lg text-[11px] font-bold bg-white focus:outline-indigo-500"
                  >
                    <option value="ALL">All NIC Industry Sectors</option>
                    <option value="NIC_A">Section A: Agriculture, Forestry & Fishing</option>
                    <option value="NIC_C">Section C: Manufacturing Industries</option>
                    <option value="NIC_G">Section G: Wholesale & Retail Trade</option>
                    <option value="NIC_I">Section I: Accommodation & Food Services</option>
                  </select>
                </div>
              </div>

              {/* Breadcrumb path indicator */}
              <div className="flex items-center text-[10px] font-black text-indigo-950 uppercase tracking-wider font-mono">
                <span 
                  className="cursor-pointer hover:underline"
                  onClick={() => { setZoomLevel('country'); }}
                >
                  India
                </span>
                {(zoomLevel === 'state' || zoomLevel === 'district') && (
                  <>
                    <ChevronRight className="w-3.5 h-3.5 inline mx-1" />
                    <span 
                      className="cursor-pointer hover:underline"
                      onClick={() => { setZoomLevel('state'); }}
                    >
                      {selectedState}
                    </span>
                  </>
                )}
                {zoomLevel === 'district' && (
                  <>
                    <ChevronRight className="w-3.5 h-3.5 inline mx-1" />
                    <span 
                      className="cursor-pointer hover:underline"
                    >
                      {selectedDistrict}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Render Map SVGs based on current zoomLevel */}
            <div className="border border-slate-150 rounded-xl bg-slate-50/50 p-4 relative min-h-[380px] flex items-center justify-center">
              
              {zoomLevel === 'country' && (
                <div className="w-full text-center space-y-3">
                  <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">
                    Interactive National Coverage Map (Avg Quality Rating)
                  </div>
                  
                  {/* Styled geographical polygon bounds represent states of India */}
                  <div className="max-w-[420px] mx-auto">
                    <svg viewBox="0 0 400 400" className="w-full h-auto drop-shadow-xl" role="img" aria-label="India National map choropleth view">
                      {/* State definitions */}
                      {Object.entries(stateStats).map(([stateName, info]) => {
                        const points = getStatePolygonPoints(stateName);
                        if (!points) return null;

                        // Flat Fill logic vs colorblind pattern fill logic
                        let strokeColor = "#cbd5e1";
                        let fillVal = "#10b981"; // high conf (green)
                        
                        if (info.confidence < 70) {
                          // Red
                          fillVal = isColorBlind ? "url(#diagonal-stripes-red)" : "#ef4444";
                        } else if (info.confidence < 80) {
                          // Amber
                          fillVal = isColorBlind ? "url(#cross-stripes-amber)" : "#fbbf24";
                        } else {
                          // Green
                          fillVal = isColorBlind ? "url(#dotted-matrix-green)" : "#10b981";
                        }

                        const isSelected = selectedState === stateName;

                        return (
                          <g key={stateName} className="cursor-pointer group" onClick={() => {
                            setSelectedState(stateName);
                            setZoomLevel('state');
                          }}>
                            <polygon
                              points={points}
                              fill={fillVal}
                              stroke={isSelected ? "#1e1b4b" : strokeColor}
                              strokeWidth={isSelected ? "3" : "1"}
                              className="transition-all duration-150 hover:opacity-85 hover:stroke-indigo-950"
                            />
                            
                            {/* Simple text centroid coordinates */}
                            <text 
                              x={Number(points.split(' ')[0].split(',')[0]) + 15}
                              y={Number(points.split(' ')[0].split(',')[1]) + 15}
                              className="fill-slate-900 font-mono text-[8px] font-black pointer-events-none text-center"
                            >
                              {info.id}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  </div>

                  <p className="text-[10px] text-slate-500 max-w-sm mx-auto font-medium">
                    * Interactive territory map displays baseline high-volume territories. Use the LGD registry below to drill into any state or union territory.
                  </p>

                  <div className="max-h-36 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 text-left">
                    <div className="mb-1 text-[9px] font-black uppercase tracking-wider text-slate-400">All LGD state / UT filters</div>
                    <div className="grid grid-cols-2 gap-1 md:grid-cols-3">
                      {stateOptions.map(state => (
                        <button
                          key={state}
                          onClick={() => {
                            setSelectedState(state);
                            setZoomLevel('state');
                            setPinFilter('');
                          }}
                          className={`rounded border px-2 py-1 text-left text-[10px] font-bold transition-colors ${
                            selectedState === state ? 'border-indigo-900 bg-indigo-50 text-indigo-900' : 'border-slate-100 bg-slate-50 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          <span className="font-mono">{stateStats[state]?.id || '--'}</span> {state}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {zoomLevel === 'state' && (
                <div className="w-full text-center space-y-4">
                  <div className="text-[10.5px] font-black text-slate-700 tracking-wide uppercase">
                    Districts inside {selectedState} Region (Choropleth Mode)
                  </div>

                  <div className="max-w-[340px] mx-auto grid grid-cols-2 gap-4">
                    {Object.entries(districtStatsTN).map(([distName, info]) => {
                      let bg = "bg-emerald-50 border-emerald-300 text-emerald-950";
                      
                      if (info.confidence < 70) bg = "bg-rose-50 border-rose-300 text-rose-950";
                      else if (info.confidence < 80) bg = "bg-amber-50 border-amber-300 text-amber-950";

                      return (
                        <div
                          key={distName}
                          onClick={() => {
                            setSelectedDistrict(distName);
                            setZoomLevel('district');
                          }}
                          className={`p-4 border-2 rounded-2xl cursor-pointer text-left shadow-sm hover:ring-2 hover:ring-indigo-950 transition-all ${
                            selectedDistrict === distName ? 'border-indigo-950 ring-2 ring-indigo-200' : ''
                          } ${bg}`}
                        >
                          <span className="font-mono text-[9px] font-black block text-slate-500 uppercase tracking-widest">
                            LGD ID: {info.id}
                          </span>
                          <h4 className="text-xs font-black mt-1 font-sans">{info.name}</h4>
                          <p className="text-[10px] mt-2 font-bold">Conf: <strong className="font-mono">{info.confidence}%</strong></p>
                          <p className="text-[9.5px] text-slate-500 mt-1 font-semibold">{info.responses} active returns</p>
                        </div>
                      );
                    })}
                  </div>

                  <button 
                    onClick={() => setZoomLevel('country')}
                    className="px-3.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-[10.5px] font-extrabold rounded-lg inline-flex items-center gap-1.5 transition-colors border"
                  >
                    <ChevronLeft className="w-4 h-4" /> Back to India map
                  </button>
                </div>
              )}

              {zoomLevel === 'district' && (
                <div className="w-full text-center space-y-4 animate-fadeIn">
                  <div className="text-[11px] font-black text-indigo-950 uppercase tracking-wide">
                    Respondent LGD Dot Map: {selectedState} &rarr; {selectedDistrict}
                  </div>

                  {/* Leaflet Live Map Integration */}
                  <div className="w-full relative h-[320px]">
                    <LeafletMap 
                      center={[selectedLocationScope?.lat || 22.9734, selectedLocationScope?.lng || 78.6569]} 
                      zoom={pinFilter ? 13 : 9} 
                      height="320px"
                      markers={scopedResponseEntries
                        .map(({ response: item, location }) => {
                          return {
                          id: item.id,
                          lat: item.paradata.gpsLat || location.lat,
                          lng: item.paradata.gpsLng || location.lng,
                          title: `Respondent #${item.id}`,
                          subtitle: `PIN ${location.pincode}, ${location.locality} | Trust ${item.confidenceScore}%`,
                          badge: item.trustBand === 'Red' ? '⚠ Quality Flag' : '✓ Verified Secure',
                          badgeColor: item.trustBand === 'Red' ? '#E24B4A' : '#1D9E75'
                        };
                        })}
                      onMarkerClick={(id) => {
                        const found = dbResponses.find(r => r.id === id);
                        if (found) setDrilledResponse(found);
                      }}
                    />
                  </div>

                  <div className="text-[10.5px] text-slate-500 font-medium">
                    * Interactive OpenStreetMap layer filtered by LGD state, district, and pincode. Live telemetry is encrypted to secure respondent identities.
                  </div>

                  <div className="flex gap-2 justify-center">
                    <button 
                      onClick={() => setZoomLevel('state')}
                      className="px-3 py-1.2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-[10px] font-bold rounded-lg border flex items-center gap-1 transition-colors"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" /> Back to {selectedState} districts
                    </button>
                    <button 
                      onClick={() => setZoomLevel('country')}
                      className="px-3 py-1.2 bg-[#0B2E5E] hover:opacity-90 text-white text-[10px] font-bold rounded-lg border flex items-center gap-1 transition-opacity"
                    >
                      India Overview
                    </button>
                  </div>
                </div>
              )}

            </div>

          </div>

          {/* Right Rail Info column syncing selected region (35% width) */}
          <aside className="lg:col-span-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 text-left">
            <div>
              <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest block">Geographic telemetry</span>
              <h3 className="font-extrabold text-sm text-slate-950 font-mono tracking-tight flex items-center gap-1.5 mt-0.5 border-b pb-2">
                <MapPin className="w-4 h-4 text-slate-405 shrink-0" />
                {getCurrentRegionInfo().name}
              </h3>
            </div>

            <div className="space-y-4 text-xs font-semibold">
              <div className="grid grid-cols-2 gap-3.5">
                <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl">
                  <span className="text-[9px] text-indigo-500 font-bold block uppercase">LGD State Code</span>
                  <span className="text-base font-extrabold text-indigo-900 font-mono">{selectedLocationScope?.stateLgdCode || getCurrentRegionInfo().id}</span>
                </div>
                <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl">
                  <span className="text-[9px] text-indigo-500 font-bold block uppercase">LGD District Code</span>
                  <span className="text-base font-extrabold text-indigo-900 font-mono">{selectedLocationScope?.districtLgdCode || districtStatsTN[selectedDistrict]?.id || '-'}</span>
                </div>
                <div className="p-3 bg-slate-50 border rounded-xl">
                  <span className="text-[9px] text-slate-400 font-bold block uppercase">Cumulative returns</span>
                  <span className="text-base font-extrabold text-slate-900 font-mono">{getCurrentRegionInfo().responses.toLocaleString()}</span>
                </div>
                <div className="p-3 bg-slate-50 border rounded-xl">
                  <span className="text-[9px] text-slate-400 font-bold block uppercase">Avg scale rating</span>
                  <span className="text-base font-extrabold text-[#10b981] font-mono">{getCurrentRegionInfo().confidence}%</span>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <span className="text-[9px] text-slate-400 font-black uppercase tracking-wider">Active LGD scope</span>
                <p className="mt-1 text-[11px] font-bold text-slate-700">
                  {selectedState} / {selectedDistrict} / {pinFilter || 'All pincodes'}
                </p>
                <p className="mt-1 text-[10px] text-slate-500">
                  Matched pincode records: {pincodeOptions.length}. Filtered response rows: {scopedResponses.length}.
                </p>
              </div>

              <div className="p-3 bg-rose-50/20 border border-rose-100 rounded-xl space-y-1">
                <div className="flex justify-between">
                  <span className="text-[9px] text-rose-800 font-bold block uppercase">Verification Flag rate</span>
                  <span className="font-mono text-rose-700 font-bold text-center">{getCurrentRegionInfo().flagRate}%</span>
                </div>
                <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mt-1">
                  <div className="bg-rose-500 h-full rounded-full" style={{ width: `${getCurrentRegionInfo().flagRate * 10}%` }} />
                </div>
              </div>

              {/* Active enumerators in selection */}
              <div className="space-y-2">
                <span className="text-[9px] text-slate-400 font-black uppercase block tracking-wider">Top Regional Enumerators</span>
                <div className="space-y-1.5">
                  {getCurrentRegionInfo().topEnumerators.map((name, k) => (
                    <div key={k} className="p-2 border border-slate-150 rounded-lg flex items-center justify-between text-[11px] bg-slate-50/50">
                      <div className="flex items-center gap-1.5 text-slate-705 font-bold">
                        <User className="w-3.5 h-3.5 text-slate-400" />
                        <span>{name}</span>
                      </div>
                      <span className="text-[9.5px] font-mono text-slate-400">Rating: 94%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Inter-routing link */}
              <div className="pt-3 border-t">
                <button
                  onClick={() => setActiveSubTab('analytics')}
                  className="w-full py-2 bg-indigo-950 hover:bg-slate-900 text-white font-extrabold rounded-xl transition-colors flex items-center justify-center gap-2"
                >
                  <TrendingUp className="w-4 h-4" /> View in analytics link
                </button>
              </div>
            </div>
          </aside>

        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 9.3: TRUST ANALYTICS TRAJECTORIES & GRAPHS TAB */}
      {/* ======================================================== */}
      {activeSubTab === 'analytics' && (
        <div className="space-y-6" id="scd-trust-analytics">
          
          <div className="bg-white border rounded-2xl p-5 shadow-sm space-y-6">
            <div className="flex justify-between items-center border-b pb-3">
              <div>
                <h3 className="font-extrabold text-sm text-slate-950 uppercase">Quality Trajectory Analytics</h3>
                <p className="text-[10px] text-slate-500 mt-0.5">Statistical distributions, geographical intervals, and fraud indicators</p>
              </div>
              <span className="text-[11px] text-slate-450 font-bold flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" /> Log: 14 days historical depth
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Chart A: Distribution histogram */}
              <div className="p-4 bg-slate-50 border rounded-xl font-medium relative text-xs">
                <div className="flex justify-between items-center pb-2.5">
                  <span className="font-bold text-slate-800 uppercase tracking-tight text-[11px]">Respondent quality histogram</span>
                  {/* Download csv mini-action */}
                  <button 
                    onClick={() => handleDownloadChartCSV('Quality_Histogram', [
                      { range: '90-100', count: scopedResponses.filter(r => r.confidenceScore >= 90).length },
                      { range: '80-89', count: scopedResponses.filter(r => r.confidenceScore >= 80 && r.confidenceScore < 90).length },
                      { range: '60-79', count: scopedResponses.filter(r => r.confidenceScore >= 60 && r.confidenceScore < 80).length },
                      { range: '0-59', count: scopedResponses.filter(r => r.confidenceScore < 60).length }
                    ])}
                    className="p-1 hover:bg-slate-200 text-slate-500 hover:text-slate-800 rounded font-bold uppercase text-[9px] border bg-white inline-flex items-center gap-1"
                    title="Download Excel CSV data"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                </div>
                
                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={[
                      { range: '90-100%', count: scopedResponses.filter(r => r.confidenceScore >= 90).length },
                      { range: '80-89%', count: scopedResponses.filter(r => r.confidenceScore >= 80 && r.confidenceScore < 90).length },
                      { range: '60-79%', count: scopedResponses.filter(r => r.confidenceScore >= 60 && r.confidenceScore < 80).length },
                      { range: '40-59%', count: scopedResponses.filter(r => r.confidenceScore >= 40 && r.confidenceScore < 60).length },
                      { range: '0-39%', count: scopedResponses.filter(r => r.confidenceScore < 40).length }
                    ]} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="range" style={{ fontSize: 9, fill: '#64748b' }} tickLine={false} />
                      <YAxis style={{ fontSize: 9, fill: '#64748b' }} tickLine={false} />
                      <Tooltip contentStyle={{ fontSize: 10, background: '#1e293b', color: '#fff', borderRadius: '6px' }} />
                      <Bar dataKey="count" fill="#4f46e5" radius={[4, 4, 0, 0]} maxBarSize={30}>
                        <Cell fill="#10b981" />
                        <Cell fill="#34d399" />
                        <Cell fill="#fbbf24" />
                        <Cell fill="#f59e0b" />
                        <Cell fill="#ef4444" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart B: Regional trust trajectories */}
              <div className="p-4 bg-slate-50 border rounded-xl text-xs">
                <div className="flex justify-between items-center pb-2.5">
                  <span className="font-bold text-slate-800 uppercase tracking-tight text-[11px]">Regional trust trajectories over time (Line)</span>
                  <button 
                     onClick={() => handleDownloadChartCSV('Trust_Trajectories', stateStats ? Object.values(stateStats) : [])}
                     className="p-1 hover:bg-slate-200 text-slate-500 hover:text-slate-800 rounded uppercase text-[9px] border bg-white inline-flex items-center gap-1"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                </div>

                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={[
                      { day: '01/06', 'Tamil Nadu': 82, 'Maharashtra': 88, 'Uttar Pradesh': 58 },
                      { day: '03/06', 'Tamil Nadu': 84, 'Maharashtra': 89, 'Uttar Pradesh': 60 },
                      { day: '05/06', 'Tamil Nadu': 81, 'Maharashtra': 86, 'Uttar Pradesh': 59 },
                      { day: '07/06', 'Tamil Nadu': 85, 'Maharashtra': 91, 'Uttar Pradesh': 62 },
                      { day: '09/06', 'Tamil Nadu': 84, 'Maharashtra': 89, 'Uttar Pradesh': 61 }
                    ]} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                      <XAxis dataKey="day" style={{ fontSize: 9 }} tickLine={false} />
                      <YAxis style={{ fontSize: 9 }} tickLine={false} domain={[40, 100]} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 9 }} />
                      <Line type="monotone" dataKey="Tamil Nadu" stroke="#4f46e5" strokeWidth={2.5} activeDot={{ r: 5 }} />
                      <Line type="monotone" dataKey="Maharashtra" stroke="#10b981" strokeWidth={2.5} />
                      <Line type="monotone" dataKey="Uttar Pradesh" stroke="#ef4444" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Chart C: Stacked area fraud signal breakdown */}
              <div className="p-4 bg-slate-50 border rounded-xl text-xs md:col-span-2">
                <div className="flex justify-between items-center pb-2.5">
                  <span className="font-bold text-slate-800 uppercase tracking-tight text-[11px]">Fraud Signal Anomaly Breakdown (Daily Stacked Area)</span>
                  <button 
                     onClick={() => handleDownloadChartCSV('Anomalous_Breakdowns', [
                       { id: 'Speeding', val: 34 },
                       { id: 'Straightlining', val: 21 },
                       { id: 'Contradiction', val: 45 }
                     ])}
                     className="p-1 hover:bg-slate-200 text-slate-500 hover:text-slate-800 rounded uppercase text-[9px] border bg-white inline-flex items-center gap-1"
                  >
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                </div>

                <div className="h-56 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={[
                      { day: '01/06', Speeding: 12, StraightLining: 8, CrossField: 15 },
                      { day: '03/06', Speeding: 14, StraightLining: 6, CrossField: 18 },
                      { day: '05/06', Speeding: 9, StraightLining: 11, CrossField: 14 },
                      { day: '07/06', Speeding: 18, StraightLining: 15, CrossField: 22 },
                      { day: '09/06', Speeding: 15, StraightLining: 10, CrossField: 19 }
                    ]} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="day" style={{ fontSize: 9 }} />
                      <YAxis style={{ fontSize: 9 }} />
                      <Tooltip />
                      <Legend wrapperStyle={{ fontSize: 9 }} />
                      <Area type="monotone" dataKey="Speeding" stackId="1" stroke="#f43f5e" fill="#fecdd3" />
                      <Area type="monotone" dataKey="StraightLining" stackId="1" stroke="#fbbf24" fill="#fef3c7" />
                      <Area type="monotone" dataKey="CrossField" stackId="1" stroke="#6366f1" fill="#e0e7ff" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

            </div>
          </div>

        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 9.3: THE EXPORTS BUILDER & COMPLETED LOGS REGISTRY */}
      {/* ======================================================== */}
      {activeSubTab === 'exports' && (
        <div className="space-y-6" id="exports-workspace-tab">
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Pick Parameters Export Card (50% width) */}
            <div className="lg:col-span-6 bg-white border border-slate-205 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="border-b pb-2">
                <h3 className="font-extrabold text-sm text-slate-900 tracking-tight flex items-center gap-1.5 uppercase">
                  <Sliders className="w-4.5 h-4.5 text-indigo-750" />
                  National Export Query Builder
                </h3>
                <p className="text-[10px] text-slate-500 italic mt-0.5">Filter questionnaire arrays, apply confidence weights, and output certified bundles</p>
              </div>

              <div className="space-y-3.5 text-xs font-semibold text-slate-700">
                {/* Survey Selector */}
                <div className="space-y-1">
                  <label className="text-slate-500 font-bold uppercase tracking-wider text-[9px] block">Pick survey class</label>
                  <select 
                    value={selectedSurvey}
                    onChange={e => setSelectedSurvey(e.target.value)}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs font-bold focus:outline-indigo-500 bg-slate-50/50"
                  >
                    <option value="PLFS-2026">Periodic Labour Force Survey (PLFS-2026)</option>
                    <option value="HCES-2026">Household Consumer Expenditure Survey (HCES-2026)</option>
                    <option value="ASI-2026">Annual Survey of Industries (ASI-2026)</option>
                  </select>
                </div>

                {/* Territory Selector */}
                <div className="space-y-1">
                  <label className="text-slate-500 font-bold uppercase tracking-wider text-[9px] block">Pick geographical region scope</label>
                  <select 
                    value={selectedExportRegion}
                    onChange={e => {
                      setSelectedExportRegion(e.target.value);
                      if (e.target.value !== 'All India') {
                        setSelectedState(e.target.value);
                        setPinFilter('');
                      }
                    }}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs font-bold focus:outline-indigo-500 bg-slate-50/50"
                  >
                    <option value="All India">All India (Consolidated baseline)</option>
                    {stateOptions.map(state => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3.5">
                  {/* Date picker */}
                  <div className="space-y-1">
                    <label className="text-slate-500 font-bold uppercase tracking-wider text-[9px] block">Target month cycle</label>
                    <select 
                      value={selectedDate}
                      onChange={e => setSelectedDate(e.target.value)}
                      className="w-full p-2 border border-slate-200 rounded-lg text-xs font-bold focus:outline-indigo-500 bg-slate-50/50"
                    >
                      <option value="June 2026">June 2026 (Operational)</option>
                      <option value="May 2026">May 2026 (Audited)</option>
                      <option value="April 2026">April 2026 (Frozen)</option>
                    </select>
                  </div>

                  {/* Slider limits */}
                  <div className="space-y-1">
                    <label className="text-slate-500 font-bold uppercase tracking-wider text-[9px] block">Quality Threshold Cutoff: &gt;= {exportThreshold}%</label>
                    <input 
                      type="range"
                      min="40"
                      max="95"
                      value={exportThreshold}
                      onChange={e => setExportThreshold(Number(e.target.value))}
                      className="w-full accent-indigo-950 mt-1.5"
                    />
                  </div>
                </div>

                {/* Live row query preview box */}
                <div className="p-3 bg-indigo-50/50 border border-thin border-indigo-150 rounded-xl space-y-1">
                  <span className="text-[10px] text-indigo-950 font-black tracking-widest block uppercase">Live Compilation Preview</span>
                  <div className="text-sm font-bold font-mono text-slate-800">
                    Estimated qualifying dataset: <strong className="text-indigo-900">{Math.max(250, Math.round((scopedResponses.length || getCurrentRegionInfo().responses / 125) * 125)).toLocaleString('en-IN')} lines</strong>
                  </div>
                  <p className="text-[9.5px] text-slate-500 italic mt-0.5">Rows processed & cleared according to National GoI SQAF directives</p>
                </div>

                {/* Generate Button */}
                <div className="pt-2">
                  <button
                    onClick={handleGenerateExport}
                    disabled={generatingExport}
                    className="w-full py-2.5 bg-indigo-950 hover:bg-slate-900 text-white font-extrabold rounded-xl transition-all shadow-md flex items-center justify-center gap-2 disabled:bg-slate-350"
                  >
                    {generatingExport ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin text-white" />
                        Generating certified CSV dataset...
                      </>
                    ) : (
                      <>
                        <Check className="w-4 h-4" />
                        Generate Cleansed Export File
                      </>
                    )}
                  </button>
                  <div className="grid grid-cols-5 gap-2 mt-3 text-[10px] font-black">
                    {['CSV', 'XLSX', 'PDF', 'DDI XML', 'Paradata'].map(format => (
                      <button
                        key={format}
                        onClick={() => setSuccessToast(`${format} export package queued for ${selectedSurvey}.`)}
                        className="py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 hover:border-indigo-300"
                      >
                        {format}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Past Exports registry table (50% width) */}
            <div className="lg:col-span-6 bg-white border border-slate-205 rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900 tracking-tight uppercase">
                  Past Certified Exports Registry
                </h3>
                <p className="text-[10px] text-slate-500 mt-0.5">National NMDS certified CSV downloads for ministries & third-party planners</p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left" role="presentation">
                  <thead className="bg-slate-100 text-[9px] text-slate-500 font-black uppercase tracking-wider border-b">
                    <tr>
                      <th className="px-3 py-2.5">File compilation details</th>
                      <th className="px-3 py-2.5">Rows</th>
                      <th className="px-3 py-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-semibold text-xs text-slate-600">
                    {exportHistory.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/50">
                        <td className="px-3 py-3 space-y-1">
                          <div className="font-bold text-slate-900 tracking-tight font-mono">{item.filename}</div>
                          <div className="flex items-center gap-2 flex-wrap text-[9px] text-slate-400 font-medium">
                            <span className="bg-sky-50 border text-sky-800 py-0.5 px-1.5 rounded uppercase font-black tracking-widest text-[8px]">
                              SQAF/NMDS Badged
                            </span>
                            <span>Region: {item.region}</span>
                            <span>Cutoff: ≥{item.threshold}%</span>
                          </div>
                        </td>
                        <td className="px-3 py-3 font-mono font-bold text-slate-800">
                          {item.count.toLocaleString()}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <button
                            onClick={() => downloadNationalReportCSV(item.filename)}
                            className="px-2 py-1 bg-slate-50 hover:bg-slate-100 text-slate-700 hover:text-indigo-950 rounded border text-[10px] font-bold flex items-center justify-center gap-1.5 ml-auto text-end"
                          >
                            <Download className="w-3 h-3" /> Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          <div className="bg-white border border-slate-205 rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h3 className="font-extrabold text-sm text-slate-900 tracking-tight uppercase">Final National Intelligence CSV</h3>
                <p className="text-[10px] text-slate-500 mt-0.5">
                  Consolidated response, paradata, validation, LGD location, NIC, and NCO/NOC fields ready for downstream download.
                </p>
              </div>
              <button
                onClick={() => downloadNationalReportCSV(`SATARK_FINAL_NATIONAL_INTELLIGENCE_${new Date().toISOString().slice(0, 10)}.csv`)}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-2.5 text-xs font-extrabold text-white shadow-md hover:bg-emerald-800"
              >
                <Download className="h-4 w-4" />
                Download Final CSV
              </button>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="min-w-[1400px] w-full text-left">
                <thead className="bg-slate-100 text-[8.5px] text-slate-500 font-black uppercase tracking-wider">
                  <tr>
                    {nationalReportHeaders.slice(0, 14).map(header => (
                      <th key={header} className="px-2.5 py-2">{header.replace(/_/g, ' ')}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-[10px] font-semibold text-slate-650">
                  {buildNationalReportRows().slice(0, 6).map((row, rowIndex) => (
                    <tr key={`${row.Response_ID}-${rowIndex}`} className="hover:bg-slate-50">
                      {nationalReportHeaders.slice(0, 14).map(header => (
                        <td key={header} className="px-2.5 py-2 font-mono">
                          {String((row as Record<string, any>)[header] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {buildNationalReportRows().length === 0 && (
                <div className="p-6 text-center text-xs font-bold text-slate-400">
                  No response rows currently match this export filter.
                </div>
              )}
            </div>
          </div>

        </div>
      )}

      {/* ======================================================== */}
      {/* SECTION 12: DRILLDOWN REVEALER CONSOLE MODAL (READONLY) */}
      {/* ======================================================== */}
      {drilledResponse && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-white border-2 border-slate-350 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl animate-scaleUp text-left">
            
            {/* Modal header */}
            <div className="bg-indigo-950 text-white p-4 flex justify-between items-center">
              <div>
                <span className="text-[10px] bg-indigo-805 text-indigo-200 border border-indigo-700 px-2 py-0.5 rounded font-black font-mono uppercase tracking-widest">
                  MoSPI National Incident Audit Console
                </span>
                <h3 className="text-sm font-black font-mono tracking-tight mt-1">
                  Verbatim file review: #{drilledResponse.id} ({drilledResponse.surveyName})
                </h3>
              </div>
              
              <button 
                onClick={() => setDrilledResponse(null)}
                className="w-8 h-8 rounded-full bg-indigo-900/40 text-indigo-200 hover:text-white flex items-center justify-center font-bold font-mono transition-colors border border-indigo-700"
              >
                ×
              </button>
            </div>

            {/* Modal body content */}
            <div className="p-5 space-y-5 overflow-y-auto max-h-[500px]">
              
              {/* Meta indicators */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-slate-50 p-3 rounded-xl border">
                <div>
                  <span className="text-[9px] text-slate-400 uppercase font-black block">Surveyor name</span>
                  <span className="font-bold text-slate-900 truncate block">{drilledResponse.enumeratorName}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-400 uppercase font-black block">Household key</span>
                  <span className="font-bold text-slate-900 font-mono block">{drilledResponse.householdId}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-400 uppercase font-black block">National rating</span>
                  <span className="font-bold block text-rose-700 font-mono tracking-wide">{drilledResponse.confidenceScore}% {drilledResponse.trustBand}</span>
                </div>
                <div>
                  <span className="text-[9px] text-slate-400 uppercase font-black block">Audit status</span>
                  <span className="inline-block bg-amber-50 text-amber-800 px-1.5 py-0.5 rounded text-[10px] font-black uppercase">
                    {drilledResponse.status}
                  </span>
                </div>
              </div>

              {/* Answers block */}
              <div className="space-y-2">
                <h4 className="text-xs font-black text-slate-405 uppercase tracking-wide">Respondent Answers list</h4>
                
                <div className="border rounded-xl overflow-hidden divide-y text-xs">
                  {Object.entries(drilledResponse.answers).map(([qId, value]) => {
                    const triggeredRules = drilledResponse.validation.layer5_cross.status === 'fail' && qId === 'Q_INCOME';
                    return (
                      <div key={qId} className={`p-2.5 flex justify-between items-center ${
                        triggeredRules ? 'bg-rose-50/50' : 'bg-white'
                      }`}>
                        <div className="space-y-0.5">
                          <span className="font-mono text-[9px] font-bold text-slate-400 bg-slate-100 px-1 py-0.5 rounded">{qId}</span>
                          <p className="text-slate-505 font-semibold mt-0.5">
                            {qId === 'Q_OCCUPATION' ? 'What is primary labor status last week?' : 
                             qId === 'Q_INCOME' ? 'Est. Monthly wage / stipend (₹)?' : qId}
                          </p>
                        </div>
                        
                        <div className="text-right">
                          <span className="font-mono font-black text-slate-900">{value.toLocaleString()}</span>
                          {triggeredRules && (
                            <span className="block text-[8.5px] bg-rose-220 text-rose-800 font-black uppercase px-1 rounded mt-1">
                              Fails logical crosscheck
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Paradata block */}
              <div className="space-y-2">
                <h4 className="text-xs font-black text-slate-405 uppercase tracking-wide">Paradata Analysis list</h4>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-slate-50/50 border rounded-xl">
                    <span className="text-[9px] text-slate-450 uppercase block">Answering velocity median</span>
                    <strong className="font-mono text-slate-800">12.5 seconds per field</strong>
                  </div>
                  <div className="p-3 bg-slate-50/50 border rounded-xl">
                    <span className="text-[9px] text-slate-450 uppercase block">Corrections / back-space count</span>
                    <strong className="font-mono text-slate-800">{drilledResponse.paradata.corrections} times</strong>
                  </div>
                </div>
              </div>

              {/* Five grounds checklist list */}
              <div className="space-y-2">
                <h4 className="text-xs font-black text-slate-405 uppercase tracking-wide">The Five Grounds Checklist validation status</h4>
                
                <div className="space-y-1.5 text-xs text-slate-750 font-medium">
                  <div className="p-2 border rounded-lg bg-emerald-50/30 flex justify-between">
                    <span>Completeness & Ranges (Layer 1)</span>
                    <strong className="text-emerald-800 font-black">PASS ✔</strong>
                  </div>
                  <div className="p-2 border rounded-lg bg-emerald-50/30 flex justify-between">
                    <span>LGD Ward Boundaries (Layer 2)</span>
                    <strong className="text-emerald-800 font-black">PASS ✔</strong>
                  </div>
                  <div className="p-2 border rounded-lg bg-rose-50/45 border-rose-200 flex justify-between">
                    <span>Survey Consistency Reviews (Layer 3)</span>
                    <strong className="text-rose-800 font-black">FAIL ✘</strong>
                  </div>
                  <div className="p-2 border rounded-lg bg-emerald-50/30 flex justify-between">
                    <span>Answering behavior speeds (Layer 4)</span>
                    <strong className="text-emerald-800 font-black">PASS ✔</strong>
                  </div>
                  <div className="p-2 border rounded-lg bg-rose-50/45 border-rose-200 flex justify-between">
                    <span>Cross-Field contradictions (Layer 5)</span>
                    <strong className="text-rose-800 font-black font-mono">FAIL ✘</strong>
                  </div>
                </div>
              </div>

            </div>

            {/* Modal sticky actions bottom */}
            <div className="bg-slate-50 p-4 border-t flex justify-end gap-2 text-xs">
              <span className="text-[10px] text-slate-400 italic self-center mr-auto">
                * View-only profile mode. Direct resolution requires a C&QCD workspace login.
              </span>
              <button 
                onClick={() => setDrilledResponse(null)}
                className="px-4 py-2 bg-slate-900 border text-white font-extrabold rounded-xl hover:bg-slate-950 transition-colors"
              >
                Close Incidents Inspector
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
