import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';

const SendIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

const AnalysisIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
  </svg>
);

const CloseIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

const MicIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
    <line x1="12" y1="19" x2="12" y2="23"/>
    <line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
);

const MicRecordingIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor" className="text-red-500 animate-pulse">
    <circle cx="12" cy="12" r="8"/>
  </svg>
);

const AIPanel = ({ isOpen, onClose, onAddAIPins }) => {
  const { t, i18n } = useTranslation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* Initialize Web Speech API */
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = i18n.language === 'ar' ? 'ar-SA' : 'id-ID';

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setInput(transcript);
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, [i18n.language]);

  const toggleRecording = useCallback(() => {
    if (!recognitionRef.current) {
      alert(t('ai.speechNotSupported', 'خاصية الإملاء الصوتي غير مدعومة في هذا المتصفح، يرجى استخدام متصفح Chrome أو Edge.'));
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        recognitionRef.current.lang = i18n.language === 'ar' ? 'ar-SA' : 'id-ID';
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (err) {
        console.error('Error starting recognition:', err);
      }
    }
  }, [isRecording, i18n.language, t]);

  /* Flores land bounding box — keeps suggestions on the island, not in the sea */
  const FLORES_BOUNDS = { minLat: -8.95, maxLat: -8.25, minLng: 119.7, maxLng: 123.2 };

  /* Verify a coordinate is on land using Mapbox reverse geocoding.
     Land points resolve to a place/locality/address; open-sea points return nothing. */
  const isOnLand = async (lat, lng) => {
    try {
      const token = import.meta.env.VITE_MAPBOX_TOKEN;
      const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${token}&types=place,locality,neighborhood,address,poi,district&limit=1`;
      const res = await fetch(url);
      const data = await res.json();
      return Array.isArray(data.features) && data.features.length > 0;
    } catch {
      return true; /* don't block pins on a network hiccup */
    }
  };

  const parseAIResponse = async (text) => {
    let cleanText = text;
    try {
      const jsonMatch = text.match(/```json\s*([\s\S]*?)\s*```/);
      if (jsonMatch) {
        const data = JSON.parse(jsonMatch[1]);
        cleanText = text.replace(/```json\s*([\s\S]*?)\s*```/, '').trim();

        if (data.type === 'map_pins' && Array.isArray(data.pins)) {
          const validPins = [];
          let dropped = 0;
          for (const p of data.pins) {
            const lat = Number(p.latitude);
            const lng = Number(p.longitude);
            const inBounds =
              Number.isFinite(lat) && Number.isFinite(lng) &&
              lat >= FLORES_BOUNDS.minLat && lat <= FLORES_BOUNDS.maxLat &&
              lng >= FLORES_BOUNDS.minLng && lng <= FLORES_BOUNDS.maxLng;
            if (!inBounds || !(await isOnLand(lat, lng))) {
              dropped++;
              continue;
            }
            validPins.push({
              id: Date.now() + Math.random(),
              latitude: lat,
              longitude: lng,
              label: p.label || t('map.customPin'),
              reason: p.reason || '',
              timestamp: new Date().toISOString(),
              source: 'ai',
            });
          }
          if (validPins.length && onAddAIPins) onAddAIPins(validPins);
          if (dropped > 0) {
            cleanText += `\n\n> ⚠️ ${t('ai.pinsDropped', 'تم تجاهل بعض النقاط لوقوعها خارج اليابسة.')} (${dropped})`;
          }
        }
      }
    } catch (e) {
      console.error('Failed to parse AI JSON block', e);
    }
    return cleanText;
  };

  const sendMessage = async (textOverride = null) => {
    const userMessage = typeof textOverride === 'string' ? textOverride.trim() : input.trim();
    if (!userMessage || isLoading) return;

    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
      const response = await fetch(`${baseUrl}/api/ai/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: messages.slice(-5),
          language: i18n.language
        }),
      });

      if (!response.ok) throw new Error('Failed to get response');
      const data = await response.json();

      const cleanText = await parseAIResponse(data.response);
      setMessages(prev => [...prev, { role: 'assistant', content: cleanText }]);
      
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: t('sidebar.error') + ': ' + error.message 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="absolute top-0 right-0 rtl:right-auto rtl:left-0 w-full sm:w-96 h-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-l rtl:border-l-0 rtl:border-r border-slate-200/70 dark:border-slate-800/70 flex flex-col z-30 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-violet-500/20">
            <AnalysisIcon />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
              {t('ai.title')}
            </h3>
            <p className="text-[10px] text-slate-400 dark:text-slate-500">
              {t('ai.subtitle')}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          aria-label={t('ai.close', 'إغلاق')}
          className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
        >
          <CloseIcon />
        </button>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <div className="w-14 h-14 rounded-2xl bg-violet-500/10 dark:bg-violet-500/20 flex items-center justify-center mb-3 text-violet-600 dark:text-violet-400">
              <AnalysisIcon />
            </div>
            <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200 mb-1">
              {t('ai.welcome')}
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-4">
              {t('ai.welcomeDesc')}
            </p>
            <div className="flex flex-col gap-1.5 w-full text-xs">
              <button
                onClick={() => sendMessage(t('ai.quickPrompt1', 'حدد لي أفضل 5 مواقع لحفر الآبار في جزيرة فلوريس وقريبة من القرى'))}
                className="text-right rtl:text-right ltr:text-left p-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-800/80 hover:bg-slate-200/80 dark:hover:bg-slate-700/80 text-slate-700 dark:text-slate-300 font-medium transition-colors"
              >
                📍 {t('ai.quickLabel1', 'حدد أفضل 5 مواقع لحفر الآبار وقريبة من القرى')}
              </button>
              <button
                onClick={() => sendMessage(t('ai.quickPrompt2', 'ما هي التكوينات الجيولوجية وحوض ماوميري في فلوريس؟'))}
                className="text-right rtl:text-right ltr:text-left p-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-800/80 hover:bg-slate-200/80 dark:hover:bg-slate-700/80 text-slate-700 dark:text-slate-300 font-medium transition-colors"
              >
                💧 {t('ai.quickLabel2', 'تحليل حوض ماوميري والتكوين الصخري')}
              </button>
              <button
                onClick={() => sendMessage(t('ai.quickPrompt3', 'كم تكلفة حفر بئر ارتوازي في جزيرة فلوريس؟'))}
                className="text-right rtl:text-right ltr:text-left p-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-800/80 hover:bg-slate-200/80 dark:hover:bg-slate-700/80 text-slate-700 dark:text-slate-300 font-medium transition-colors"
              >
                💰 {t('ai.quickLabel3', 'تقدير تكلفة حفر بئر ارتوازي')}
              </button>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end rtl:justify-start' : 'justify-start rtl:justify-end'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs md:text-sm leading-relaxed ${
              msg.role === 'user'
                ? 'bg-violet-600 text-white rounded-br-none rtl:rounded-br-2xl rtl:rounded-bl-none shadow-md shadow-violet-600/20'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-none rtl:rounded-bl-2xl rtl:rounded-br-none border border-slate-200/60 dark:border-slate-700/60'
            }`}>
              {msg.role === 'user' ? <div className="whitespace-pre-wrap">{msg.content}</div> : <div className="space-y-2 [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:ps-5 [&_ol]:list-decimal [&_ol]:ps-5 [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-semibold"><ReactMarkdown>{msg.content}</ReactMarkdown></div>}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start rtl:justify-end">
            <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-none px-4 py-3 border border-slate-200/60 dark:border-slate-700/60 flex items-center gap-2">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 rounded-full bg-violet-600 animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-xs text-slate-400 font-medium">{t('ai.analyzing', 'جاري التحليل الهيدروجيولوجي...')}</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input & Voice Controls */}
      <div className="p-3.5 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900">
        {isRecording && (
          <div className="mb-2 flex items-center justify-between px-3 py-1.5 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-xs font-semibold animate-pulse">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
              {t('ai.listening', 'جاري الاستماع لصوتك... تكلم الآن')}
            </span>
            <button onClick={toggleRecording} className="text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 text-xs underline">
              {t('ai.stop', 'إيقاف')}
            </button>
          </div>
        )}

        <div className="flex items-end gap-2 bg-slate-50 dark:bg-slate-800/60 rounded-2xl p-2 border border-slate-200/70 dark:border-slate-700/70 focus-within:border-violet-500/60 focus-within:ring-2 focus-within:ring-violet-500/20 transition-all">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isRecording ? t('ai.speakNow', 'تحدث الآن...') : t('ai.placeholder')}
            rows={1}
            className="flex-1 resize-none bg-transparent text-xs md:text-sm text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none px-2 py-1.5 max-h-24"
          />

          {/* Voice Input Mic Button */}
          <button
            onClick={toggleRecording}
            type="button"
            aria-label={isRecording ? t('ai.stopRecording', 'إيقاف التسجيل') : t('ai.startVoice', 'تسجيل صوتي')}
            className={`p-2 rounded-xl transition-all flex-shrink-0 ${
              isRecording
                ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
                : 'text-slate-500 hover:text-violet-600 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
            title={isRecording ? t('ai.stopRecording', 'إيقاف التسجيل') : t('ai.startVoice', 'تسجيل صوتي')}
          >
            {isRecording ? <MicRecordingIcon /> : <MicIcon />}
          </button>

          {/* Send Button */}
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
            aria-label={t('ai.send', 'إرسال')}
            className="p-2 rounded-xl bg-violet-600 hover:bg-violet-700 disabled:bg-slate-200 dark:disabled:bg-slate-800 text-white disabled:text-slate-400 transition-colors flex-shrink-0 shadow-sm"
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIPanel;
