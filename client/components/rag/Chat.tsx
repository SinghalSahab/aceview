"use client";
import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  User, 
  Send, 
  Sparkles, 
  MessageSquare, 
  CornerDownLeft, 
  ArrowRight,
  ShieldCheck,
  FileCheck
} from 'lucide-react';

interface ChatComponentProps {
  data: {
    text: string;
    fileName?: string;
    fileSize?: number;
  } | null;
}

interface Message {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

const PRESET_PROMPTS = [
  { label: "Summarize document", query: "Summarize this document" },
  { label: "List my skills", query: "List my technical skills" },
  { label: "Generate interview questions", query: "Generate mock interview questions based on my background" },
];

const ChatComponent: React.FC<ChatComponentProps> = ({ data }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputVal, setInputVal] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Reset messages when document changes
  useEffect(() => {
    if (data) {
      setMessages([
        {
          id: 'welcome',
          sender: 'ai',
          text: `### Document Analysis Complete! 🚀\n\nI have successfully loaded and parsed **${data.fileName || 'your document'}**.\n\nYou can now ask me questions directly about the document contents. Select one of the quick prompts below or type your question in the chat input.`,
          timestamp: new Date()
        }
      ]);
    } else {
      setMessages([]);
    }
  }, [data]);

  const handleSendMessage = (textToSend: string) => {
    if (!textToSend.trim() || isTyping || !data) return;

    // 1. Add User Message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: textToSend,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMsg]);
    setInputVal('');
    setIsTyping(true);

    // 2. Simulate AI response with streaming
    setTimeout(() => {
      const fullResponseText = generateSmartResponse(textToSend, data.text, data.fileName || 'document.pdf');
      
      // Simulate word-by-word streaming
      const words = fullResponseText.split(' ');
      let currentWordIndex = 0;
      let streamedText = '';

      const aiMsgId = `ai-${Date.now()}`;
      
      // Add empty message container for streaming
      const initialAiMsg: Message = {
        id: aiMsgId,
        sender: 'ai',
        text: '',
        timestamp: new Date()
      };
      setIsTyping(false);
      setMessages(prev => [...prev, initialAiMsg]);

      const streamInterval = setInterval(() => {
        if (currentWordIndex < words.length) {
          streamedText += (currentWordIndex === 0 ? '' : ' ') + words[currentWordIndex];
          setMessages(prev => 
            prev.map(m => m.id === aiMsgId ? { ...m, text: streamedText } : m)
          );
          currentWordIndex++;
        } else {
          clearInterval(streamInterval);
        }
      }, 25); // Word render speed in milliseconds
      
    }, 1200 + Math.random() * 800); // Simulated delay
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputVal);
    }
  };

  // ─── Smart RAG Response Generator ─────────────────────────────────────────────
  const generateSmartResponse = (userQuery: string, documentText: string, fileName: string): string => {
    const query = userQuery.toLowerCase().trim();
    if (!documentText) {
      return "I don't have any text from the document to analyze. Please try uploading it again.";
    }

    const textLower = documentText.toLowerCase();

    // 1. SUMMARY
    if (query.includes("summar") || query.includes("overview") || query.includes("what is this") || query.includes("about")) {
      const lines = documentText.split('\n').map(l => l.trim()).filter(Boolean);
      const nameLine = lines[0] || "the candidate";
      const wordCount = documentText.split(/\s+/).length;
      
      const isResume = textLower.includes("experience") || textLower.includes("education") || textLower.includes("skills") || textLower.includes("work");
      
      if (isResume) {
        const detectedSkills: string[] = [];
        const commonSkills = ["react", "next.js", "typescript", "javascript", "python", "flask", "django", "node", "express", "sql", "mongodb", "aws", "docker", "kubernetes", "c++", "java", "html", "css", "tailwind", "git"];
        commonSkills.forEach(skill => {
          if (textLower.includes(skill)) {
            detectedSkills.push(skill.charAt(0).toUpperCase() + skill.slice(1));
          }
        });

        return `### Document Analysis Summary 📝\n\nBased on my analysis of **${fileName}**, this document appears to be a professional resume or portfolio profile.\n\n* **Primary Subject:** ${nameLine}\n* **File Statistics:** ~${wordCount} words analyzed.\n* **Identified Tech Stack:** ${detectedSkills.slice(0, 8).join(", ") || "General tech background"}\n* **Key Sections Found:** ${textLower.includes("experience") ? "Work Experience, " : ""}${textLower.includes("education") ? "Education, " : ""}${textLower.includes("project") ? "Projects" : ""}\n\n**Quick Takeaways:**\nThis candidate has a strong background in modern application development. To check specifics, try asking me about **experience details**, **education credentials**, or **technical skills**!`;
      } else {
        const snippet = lines.slice(0, 10).join(' ');
        return `### Document Summary 📄\n\nThis document (**${fileName}**) appears to contain preparation materials, guidelines, or technical concepts.\n\n* **Word Count:** Approx. ${wordCount} words\n* **Content Snippet:** "${snippet.substring(0, 200)}..."\n\nYou can ask me specific questions about technical guidelines, terms, or conceptual notes parsed from the file.`;
      }
    }

    // 2. SKILLS
    if (query.includes("skill") || query.includes("tech") || query.includes("tool") || query.includes("language") || query.includes("profici")) {
      const commonSkills = [
        { name: "React / React Native", keywords: ["react"] },
        { name: "Next.js", keywords: ["next.js", "nextjs"] },
        { name: "TypeScript", keywords: ["typescript", "ts"] },
        { name: "JavaScript", keywords: ["javascript", "js"] },
        { name: "Python", keywords: ["python", "py"] },
        { name: "Flask / Django", keywords: ["flask", "django"] },
        { name: "Node.js (Express)", keywords: ["node.js", "nodejs", "node", "express"] },
        { name: "MongoDB", keywords: ["mongodb", "mongo"] },
        { name: "SQL (PostgreSQL/MySQL)", keywords: ["sql", "postgres", "mysql"] },
        { name: "AWS (Amazon Web Services)", keywords: ["aws", "amazon"] },
        { name: "Docker & Containerization", keywords: ["docker"] },
        { name: "Kubernetes", keywords: ["kubernetes", "k8s"] },
        { name: "HTML & CSS", keywords: ["html", "css"] },
        { name: "Tailwind CSS", keywords: ["tailwind"] },
        { name: "Prisma ORM", keywords: ["prisma"] },
        { name: "Git & Version Control", keywords: ["git", "github"] }
      ];

      const found = commonSkills.filter(s => s.keywords.some(kw => textLower.includes(kw))).map(s => s.name);

      if (found.length > 0) {
        return `### Technical Skills & Technologies Found 🛠️\n\nHere are the technical skills and toolsets extracted from **${fileName}**:\n\n${found.map(skill => `* **${skill}**`).join("\n")}\n\nWould you like me to generate specialized mock interview questions based on this stack?`;
      } else {
        return `### Skills & Capabilities\n\nI searched for common technologies but didn't find standard keyword matches. Here are lines from the document that might discuss skills:\n\n${documentText.split('\n').filter(line => line.toLowerCase().includes("skill") || line.toLowerCase().includes("expert") || line.toLowerCase().includes("familiar")).slice(0, 3).map(line => `> ${line}`).join("\n\n") || "No explicit references found. Try asking about past projects or education!"}`;
      }
    }

    // 3. EXPERIENCE
    if (query.includes("experience") || query.includes("work") || query.includes("job") || query.includes("career") || query.includes("employ") || query.includes("history")) {
      const paragraphs = documentText.split('\n\n').filter(p => p.trim().length > 15);
      const expParagraphs = paragraphs.filter(p => {
        const pLower = p.toLowerCase();
        return pLower.includes("experience") || pLower.includes("engineer") || pLower.includes("developer") || pLower.includes("manager") || pLower.includes("intern") || pLower.includes("work at");
      });

      if (expParagraphs.length > 0) {
        return `### Work Experience Highlights 💼\n\nHere is what I found regarding work history or practical experience in the document:\n\n${expParagraphs.slice(0, 2).map(p => `${p.trim()}\n\n---\n`).join("\n")}\nWould you like me to generate typical behavioral questions (e.g. *Amazon Leadership Principles*) based on these roles?`;
      }

      // Check lines
      const expLines = documentText.split('\n').filter(l => {
        const lLower = l.toLowerCase();
        return lLower.includes("experience") || lLower.includes("work") || lLower.includes("company") || lLower.includes("role");
      });
      
      if (expLines.length > 0) {
        return `### Experience References\n\nI located these work-related details in the document:\n\n${expLines.slice(0, 4).map(l => `* ${l.trim()}`).join("\n")}`;
      }
      return `### Experience Analysis\n\nI could not find an explicit section outlining work history. The document may be a guidelines document. Let me know if you would like me to extract other conceptual details!`;
    }

    // 4. EDUCATION
    if (query.includes("education") || query.includes("university") || query.includes("college") || query.includes("school") || query.includes("degree") || query.includes("gpa")) {
      const eduLines = documentText.split('\n').filter(l => {
        const lLower = l.toLowerCase();
        return lLower.includes("education") || lLower.includes("university") || lLower.includes("college") || lLower.includes("bachelor") || lLower.includes("master") || lLower.includes("degree") || lLower.includes("gpa") || lLower.includes("school");
      });

      if (eduLines.length > 0) {
        return `### Academic & Education Background 🎓\n\nHere are the academic achievements and education records extracted from the file:\n\n${eduLines.slice(0, 4).map(line => `* **${line.trim()}**`).join("\n")}`;
      }
      return `### Education Details\n\nI couldn't locate education references. If it's a technical preparation sheet, try asking about algorithms or system design concepts instead!`;
    }

    // 5. INTERVIEW QUESTIONS
    if (query.includes("interview") || query.includes("question") || query.includes("practice") || query.includes("test")) {
      const isReact = textLower.includes("react") || textLower.includes("next");
      const isPython = textLower.includes("python") || textLower.includes("flask") || textLower.includes("django");
      
      let questions = [
        "What was the most challenging technical project you worked on, and how did you resolve the bottlenecks?",
        "How do you approach writing clean, testable code, and what metrics do you use to evaluate code quality?",
        "Explain the key architectural differences between RESTful APIs and GraphQL, and their respective trade-offs."
      ];

      if (isReact) {
        questions = [
          "Explain the difference between Server Components and Client Components in Next.js 14+, and when to use use client.",
          "How does React's virtual DOM reconciliation work, and how does the key prop assist this process?",
          "How would you diagnose and optimize a performance issue in a heavy scrollable listing component in React?"
        ];
      } else if (isPython) {
        questions = [
          "How does Python's Global Interpreter Lock (GIL) impact multi-threaded performance, and how do you achieve true parallelism?",
          "Describe how you handle request state and database connection pooling in Flask backend routes.",
          "What are the differences between generators and iterators in Python, and when would you use them to optimize memory?"
        ];
      }

      return `### Generated Interview Practice Questions 🎯\n\nBased on the skills parsed from **${fileName}**, I recommend preparing responses for the following questions:\n\n1. **Technical Depth:**\n   *${questions[0]}*\n\n2. **Framework / Architecture:**\n   *${questions[1]}*\n\n3. **Performance Optimization:**\n   *${questions[2]}*\n\nTo view sample answer templates, you can ask: *"Give me a sample answer for Question 1"*`;
    }

    // 6. SAMPLE ANSWERS
    if (query.includes("sample answer") || query.includes("answer for") || query.includes("question 1") || query.includes("question 2") || query.includes("question 3")) {
      return `### Structured Answer Template (STAR Method) 📝\n\nTo answer this question effectively, structure your response as follows:\n\n* **Situation (15%):** Describe the context. *"While working on a web dashboard, we faced rendering lag when..."*\n* **Task (15%):** The goal. *"We needed to reduce render times by 50% without dropping features."*\n* **Action (50%):** What you did. *"I analyzed component render cycles, implemented virtualization using react-window, and memoized expensive filters..."*\n* **Result (20%):** The success. *"This resolved the layout lag, cut CPU usage by 35%, and improved our UX scores."*\n\nUsing this structured format ensures you hit all key points during your live interview.`;
    }

    // 7. KEYWORD / RAG REFERENCE SEARCH
    const keywords = query.split(/\s+/).filter(w => w.length > 3 && !["what", "when", "where", "how", "this", "that", "with", "from", "about", "your", "have"].includes(w));
    
    if (keywords.length > 0) {
      const segments = documentText.split(/[.!?\n]+/).map(s => s.trim()).filter(s => s.length > 20);
      
      const scoredSegments = segments.map(seg => {
        const segLower = seg.toLowerCase();
        let score = 0;
        keywords.forEach(kw => {
          if (segLower.includes(kw)) score += 1;
        });
        return { text: seg, score };
      }).filter(s => s.score > 0);

      scoredSegments.sort((a, b) => b.score - a.score);

      if (scoredSegments.length > 0) {
        const matches = scoredSegments.slice(0, 3).map(s => `> "... ${s.text} ..."`).join("\n\n");
        return `### Extracted Document Context 🔍\n\nI searched the document and found the following relevant matches:\n\n${matches}\n\n*Feel free to ask more specific questions based on these references!*`;
      }
    }

    // 8. DEFAULT FALLBACK
    return `### Document Assistant 🤖\n\nI analyzed your query: *"${userQuery}"*.\n\nI couldn't find a direct keyword match inside **${fileName}**. However, you can check the full document content directly by clicking **"View Text"** in the sidebar.\n\nTry asking:\n* *"Give me a summary"* \n* *"What are my technical skills?"* \n* *"Generate interview questions"*`;
  };

  // Helper to render markdown headings and bold text simply
  const renderText = (text: string) => {
    return text.split('\n').map((line, index) => {
      let content: React.ReactNode = line;
      let className = "text-sm text-neutral-200 leading-relaxed my-1.5";

      if (line.startsWith('### ')) {
        content = line.replace('### ', '');
        className = "text-base font-bold text-white mt-4 mb-2 flex items-center gap-1.5";
      } else if (line.startsWith('* ')) {
        const rest = line.replace('* ', '');
        className = "text-sm text-neutral-300 ml-4 list-disc my-1";
        content = parseBold(rest);
      } else if (line.startsWith('1. ') || line.startsWith('2. ') || line.startsWith('3. ')) {
        className = "text-sm text-neutral-300 ml-4 my-1.5";
        content = parseBold(line);
      } else if (line.startsWith('> ')) {
        content = line.replace('> ', '');
        className = "text-xs text-neutral-400 border-l-2 border-purple-500/50 pl-3 py-1 my-2 bg-purple-500/5 rounded-r font-mono italic";
      } else {
        content = parseBold(line);
      }

      if (line.trim() === '---') {
        return <hr key={index} className="border-t border-white/5 my-4" />;
      }

      return <p key={index} className={className}>{content}</p>;
    });
  };

  // Bold parser helper
  const parseBold = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col h-full min-h-[450px]">
      {/* Empty State */}
      {!data ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-black/10">
          <div className="relative mb-6">
            <div className="absolute -inset-1.5 rounded-full bg-purple-500/20 blur-lg animate-pulse" />
            <div className="relative bg-white/5 border border-white/10 rounded-full p-5 text-purple-400">
              <MessageSquare className="w-10 h-10" />
            </div>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Interactive Document Chat</h2>
          <p className="text-sm text-neutral-400 max-w-sm mb-6 leading-relaxed">
            Upload your resume or study PDF in the left panel to begin a smart, context-aware RAG chat.
          </p>
          <div className="text-xs text-yellow-500/80 bg-yellow-500/5 border border-yellow-500/10 px-4 py-2.5 rounded-xl flex items-center gap-2 max-w-xs justify-center font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-ping" />
            <span>Awaiting document upload...</span>
          </div>
        </div>
      ) : (
        /* Active Chat Client */
        <div className="flex-1 flex flex-col h-full bg-black/10 overflow-hidden">
          {/* Active Chat Header */}
          <div className="px-6 py-4 border-b border-white/5 bg-[#0b0b14]/40 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-2 text-purple-400">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">Document Assistant</h3>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  <span className="text-[11px] text-neutral-400 truncate max-w-[200px] sm:max-w-xs font-mono">
                    Connected: {data.fileName}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-1.5 text-xs text-green-400 bg-green-500/5 border border-green-500/10 px-2.5 py-1.5 rounded-lg font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">RAG Context Secured</span>
              <span className="inline sm:hidden">Secured</span>
            </div>
          </div>

          {/* Chat History Container */}
          <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-5 scrollbar-thin scrollbar-thumb-white/5 hover:scrollbar-thumb-white/10">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${msg.sender === 'user' ? 'self-end flex-row-reverse' : 'self-start'}`}
              >
                {/* Avatar */}
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border text-white
                  ${msg.sender === 'user' 
                    ? 'bg-gradient-to-br from-indigo-500 to-purple-600 border-indigo-400/20' 
                    : 'bg-white/5 border-white/10 text-purple-400'
                  }`}
                >
                  {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                </div>

                {/* Message Bubble */}
                <div className={`px-4 py-3 rounded-2xl shadow-md border
                  ${msg.sender === 'user'
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 border-purple-500/20 text-white rounded-tr-none'
                    : 'bg-[#151524]/80 border-white/5 text-neutral-200 rounded-tl-none'
                  }`}
                >
                  <div className="text-sm prose prose-invert select-text">
                    {msg.sender === 'ai' ? renderText(msg.text) : <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>}
                  </div>
                  <span className="block text-[9px] text-neutral-400/80 text-right mt-1.5 font-mono select-none">
                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            ))}

            {/* AI Typing Indicator */}
            {isTyping && (
              <div className="flex gap-3 max-w-[85%] self-start">
                <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-white/5 border border-white/10 text-purple-400">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-[#151524]/80 border border-white/5 px-4 py-3.5 rounded-2xl rounded-tl-none shadow-md flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Prompt Chips (Visible when chat starts) */}
          {messages.length <= 1 && !isTyping && (
            <div className="px-6 py-2 flex flex-wrap gap-2.5 select-none bg-gradient-to-t from-[#0b0b14]/50 to-transparent">
              <span className="text-[11px] font-semibold text-neutral-400 flex items-center gap-1 w-full mb-1">
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>Try asking:</span>
              </span>
              {PRESET_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendMessage(prompt.query)}
                  className="text-xs bg-white/5 hover:bg-purple-500/10 text-neutral-300 hover:text-purple-300 px-3.5 py-2 rounded-xl border border-white/10 hover:border-purple-500/20 transition-all duration-200 flex items-center gap-1.5 cursor-pointer"
                >
                  <span>{prompt.label}</span>
                  <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          )}

          {/* Input Panel */}
          <div className="p-4 sm:p-6 border-t border-white/5 bg-[#0b0b14]/40">
            <div className="relative flex items-center bg-[#13131d]/60 border border-white/10 rounded-2xl focus-within:border-purple-500/40 focus-within:shadow-[0_0_20px_rgba(147,51,234,0.06)] transition-all duration-300 px-4 py-2">
              <textarea
                value={inputVal}
                onChange={(e) => setInputVal(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about the document..."
                rows={1}
                className="flex-1 bg-transparent text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none resize-none max-h-24 py-2 font-normal leading-relaxed pr-12 scrollbar-none"
              />
              
              <button
                type="button"
                onClick={() => handleSendMessage(inputVal)}
                disabled={!inputVal.trim() || isTyping}
                className={`absolute right-3 p-2 rounded-xl text-white transition-all duration-200 cursor-pointer
                  ${inputVal.trim() && !isTyping
                    ? 'bg-purple-600 hover:bg-purple-500 shadow-md shadow-purple-500/10'
                    : 'bg-white/5 text-neutral-500 cursor-not-allowed'
                  }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            
            <div className="flex items-center justify-between mt-2.5 px-1.5 select-none">
              <span className="text-[10px] text-neutral-500 flex items-center gap-1">
                <FileCheck className="w-3.5 h-3.5" />
                <span>Matches queries against active document content</span>
              </span>
              <span className="text-[10px] text-neutral-500 hidden sm:flex items-center gap-1">
                <span>Press Enter to send</span>
                <CornerDownLeft className="w-3 h-3" />
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatComponent;