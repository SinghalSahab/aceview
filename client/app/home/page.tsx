"use client"
import React from "react";
import Link from "next/link";
import { Calendar, Star } from "lucide-react";
import Image from "next/image";
import { InterviewDashboard } from "@/components/dashboard/InterviewDashboard";

// ─── Types ─────────────────────────────────────────────────────────────────────
interface Interview {
  id: number;
  company: string;
  companyColor: string;
  companyInitial: string;
  title: string;
  type: "Technical" | "Non-Technical";
  date?: string;
  score?: string;
  description: string;
  techStack: string[];
  action: "View interview" | "Take interview";
}

// ─── Data ──────────────────────────────────────────────────────────────────────
const pastInterviews: Interview[] = [
  {
    id: 1,
    company: "HackerRank",
    companyColor: "#6c47ff",
    companyInitial: "H",
    title: "Frontend Dev Interview",
    type: "Technical",
    date: "Feb 28, 2025",
    score: "12/100",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "View interview",
  },
  {
    id: 2,
    company: "Facebook",
    companyColor: "#1877f2",
    companyInitial: "f",
    title: "Behavioral Interview",
    type: "Non-Technical",
    date: "Feb 23, 2025",
    score: "54/100",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "View interview",
  },
  {
    id: 3,
    company: "Adobe",
    companyColor: "#e1251b",
    companyInitial: "A",
    title: "Backend Dev Interview",
    type: "Technical",
    date: "Feb 21, 2025",
    score: "94/100",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "View interview",
  },
];

const availableInterviews: Interview[] = [
  {
    id: 4,
    company: "Yahoo",
    companyColor: "#6001d2",
    companyInitial: "y!",
    title: "Full-Stack Dev Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 5,
    company: "Reddit",
    companyColor: "#ff4500",
    companyInitial: "R",
    title: "DevOps & Cloud Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 6,
    company: "Telegram",
    companyColor: "#2aabee",
    companyInitial: "T",
    title: "HR Screening Interview",
    type: "Non-Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 7,
    company: "Dropbox",
    companyColor: "#0061ff",
    companyInitial: "D",
    title: "System Design Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 8,
    company: "Spotify",
    companyColor: "#1ed760",
    companyInitial: "S",
    title: "Business Analyst Interview",
    type: "Non-Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 9,
    company: "Quora",
    companyColor: "#b92b27",
    companyInitial: "Q",
    title: "Mobile App Dev Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 10,
    company: "Pinterest",
    companyColor: "#e60023",
    companyInitial: "P",
    title: "Data Science Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 11,
    company: "Skype",
    companyColor: "#00aff0",
    companyInitial: "S",
    title: "Cloud Architecture Interview",
    type: "Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
  {
    id: 12,
    company: "TikTok",
    companyColor: "#010101",
    companyInitial: "T",
    title: "Product Manager Interview",
    type: "Non-Technical",
    description:
      "This interview does not reflect serious interest or engagement from the candidate. Their responses are dismissiv...",
    techStack: ["react", "tailwind"],
    action: "Take interview",
  },
];

// ─── Sub-components ────────────────────────────────────────────────────────────

const ReactIcon = () => (
  <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 22, height: 22 }}>
    <circle cx="20" cy="20" r="20" fill="#1a1a2e" />
    <circle cx="20" cy="20" r="3" fill="#61dafb" />
    <ellipse cx="20" cy="20" rx="10" ry="4.5" stroke="#61dafb" strokeWidth="1.3" fill="none" />
    <ellipse cx="20" cy="20" rx="10" ry="4.5" stroke="#61dafb" strokeWidth="1.3" fill="none" transform="rotate(60 20 20)" />
    <ellipse cx="20" cy="20" rx="10" ry="4.5" stroke="#61dafb" strokeWidth="1.3" fill="none" transform="rotate(120 20 20)" />
  </svg>
);

const TailwindIcon = () => (
  <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 22, height: 22 }}>
    <circle cx="20" cy="20" r="20" fill="#1a1a2e" />
    <path
      d="M11 18c1-4 3.5-6 7.5-5.5 2.5.3 4 2 4.5 5-.5-2.5 1-5 4-5.5 3-.5 5 1 6 3.5-1.5.5-3 1.5-4.5 2.5-1 .8-1.8 1.8-2.5 3-1-2.5-2.5-4-5-4.5C18.5 16 17 17 16 19c-1-1-1.5-1.5-5-1z"
      fill="#38bdf8"
    />
    <path
      d="M11 25c1-4 3.5-6 7.5-5.5 2.5.3 4 2 4.5 5-.5-2.5 1-5 4-5.5 3-.5 5 1 6 3.5-1.5.5-3 1.5-4.5 2.5-1 .8-1.8 1.8-2.5 3-1-2.5-2.5-4-5-4.5C18.5 23 17 24 16 26c-1-1-1.5-1.5-5-1z"
      fill="#38bdf8"
    />
  </svg>
);

const CompanyAvatar = ({
  color,
  initial,
  company,
}: {
  color: string;
  initial: string;
  company: string;
}) => (
  <div
    aria-label={company}
    style={{
      width: 56,
      height: 56,
      borderRadius: "50%",
      backgroundColor: color,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#fff",
      fontWeight: 700,
      fontSize: 20,
      flexShrink: 0,
    }}
  >
    {initial}
  </div>
);

const Badge = ({ type }: { type: "Technical" | "Non-Technical" }) => (
  <span
    style={{
      background: type === "Non-Technical" ? "#3b5bdb" : "rgba(255,255,255,0.10)",
      color: "#fff",
      fontSize: 12,
      fontWeight: 500,
      padding: "4px 12px",
      borderRadius: 6,
      whiteSpace: "nowrap" as const,
    }}
  >
    {type}
  </span>
);

const InterviewCard = ({ interview }: { interview: Interview }) => (
  <article
    style={{
      background: "#13131d",
      border: "1px solid rgba(255,255,255,0.07)",
      borderRadius: 18,
      padding: "20px",
      display: "flex",
      flexDirection: "column",
      gap: 14,
      minWidth: 270,
      maxWidth: 320,
      transition: "transform 0.2s, box-shadow 0.2s",
      cursor: "default",
    }}
    onMouseEnter={(e) => {
      (e.currentTarget as HTMLElement).style.transform = "scale(1.025)";
      (e.currentTarget as HTMLElement).style.boxShadow = "0 20px 50px rgba(0,0,0,0.5)";
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLElement).style.transform = "scale(1)";
      (e.currentTarget as HTMLElement).style.boxShadow = "none";
    }}
  >
    {/* Top: avatar + badge */}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <CompanyAvatar color={interview.companyColor} initial={interview.companyInitial} company={interview.company} />
      <Badge type={interview.type} />
    </div>

    {/* Title + meta */}
    <div>
      <h3 style={{ color: "#fff", fontWeight: 700, fontSize: 18, lineHeight: 1.3, marginBottom: 6 }}>
        {interview.title}
      </h3>
      {interview.date && (
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 5, color: "#a1a1aa", fontSize: 12 }}>
            <Calendar size={13} /> {interview.date}
          </span>
          <span style={{ display: "flex", alignItems: "center", gap: 5, color: "#a1a1aa", fontSize: 12 }}>
            <Star size={13} /> {interview.score}
          </span>
        </div>
      )}
    </div>

    {/* Description */}
    <p
      style={{
        color: "#a1a1aa",
        fontSize: 13,
        lineHeight: 1.6,
        display: "-webkit-box",
        WebkitLineClamp: 3,
        WebkitBoxOrient: "vertical" as const,
        overflow: "hidden",
      } as React.CSSProperties}
    >
      {interview.description}
    </p>

    {/* Divider for available interviews */}
    {!interview.date && (
      <hr style={{ border: "none", borderTop: "1px solid rgba(255,255,255,0.07)" }} />
    )}

    {/* Bottom: tech icons + CTA */}
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "auto" }}>
      <div style={{ display: "flex", gap: 4 }}>
        <ReactIcon />
        <TailwindIcon />
      </div>
      <button
        type="button"
        style={{
          background: "#cac5fe",
          color: "#0b0b14",
          border: "none",
          borderRadius: 9999,
          padding: "8px 20px",
          fontSize: 13,
          fontWeight: 600,
          cursor: "pointer",
          transition: "opacity 0.15s",
        }}
        onMouseEnter={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "0.85")}
        onMouseLeave={(e) => ((e.currentTarget as HTMLButtonElement).style.opacity = "1")}
      >
        {interview.action}
      </button>
    </div>
  </article>
);



// ─── Page ──────────────────────────────────────────────────────────────────────
const HomePage = () => {
  const pageStyle: React.CSSProperties = {
    backgroundColor: "#0b0b14",
    minHeight: "100vh",
    fontFamily: "'Geist', 'Inter', sans-serif",
  };

  const gridBg: React.CSSProperties = {
    backgroundImage:
      "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
    backgroundSize: "55px 55px",
  };

  return (
    <div style={pageStyle}>
      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <nav style={{ display: "flex", alignItems: "center", padding: "20px 40px" }}>
        <Link href="/home" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none" }}>
          {/* Logo */}
          <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 32, height: 32 }}>
            <circle cx="16" cy="16" r="16" fill="rgba(232,168,124,0.15)" />
            <path
              d="M8 12C8 9.8 9.8 8 12 8H20C22.2 8 24 9.8 24 12V18C24 20.2 22.2 22 20 22H17L13 26V22H12C9.8 22 8 20.2 8 18V12Z"
              fill="#e8a87c"
            />
            <path d="M12 14.5C12 14.5 13.5 13 16 13C18.5 13 20 14.5 20 14.5" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M12 17C12 17 13.5 15.5 16 15.5C18.5 15.5 20 17 20 17" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>AceView</span>
        </Link>
      </nav>

      <main style={{ padding: "0 40px 60px", maxWidth: 1400, margin: "0 auto" }}>
        {/* ── Hero ──────────────────────────────────────────────────────── */}
        <section
          style={{
            ...gridBg,
            background: "linear-gradient(135deg, #11112a 0%, #1a1040 60%, #0e0e24 100%)",
            borderRadius: 24,
            border: "1px solid rgba(255,255,255,0.06)",
            position: "relative",
            overflow: "hidden",
            minHeight: 300,
            display: "flex",
            alignItems: "center",
            marginBottom: 56,
          }}
        >
          {/* Left content */}
          <div style={{ padding: "48px 52px", maxWidth: 560, position: "relative", zIndex: 1 }}>
            <h1
              style={{
                color: "#fff",
                fontWeight: 700,
                fontSize: "clamp(28px, 3.5vw, 44px)",
                lineHeight: 1.2,
                marginBottom: 16,
              }}
            >
              Get Interview-Ready with AI-Powered Practice &amp; Feedback
            </h1>
            <p style={{ color: "#a1a1aa", fontSize: 17, marginBottom: 32 }}>
              Practice real interview questions &amp; get instant feedback.
            </p>
            <Link
              href="/interview/start"
              id="start-interview-btn"
              style={{
                display: "inline-block",
                background: "#cac5fe",
                color: "#0b0b14",
                borderRadius: 9999,
                padding: "14px 32px",
                fontWeight: 600,
                fontSize: 15,
                textDecoration: "none",
                transition: "opacity 0.2s",
              }}
            >
              Start an Interview
            </Link>
          </div>

          {/* Right: floating badges + robot */}
         <div
  style={{
    position: "absolute",
    right: 0,
    bottom: -10,
    width: 480,
    height: "100%",
    overflow: "hidden", 
  }}
>
  <Image 
    src="/robot.png" 
    alt="Robot" 
    fill 
    style={{
      objectFit: "contain", 
      objectPosition: "bottom right", 
    }} 
  />
</div>
        </section>

        {/* ── Candidate Resumes & Mock Interview Launcher ─────────── */}
        <section style={{ marginBottom: 56 }}>
          <InterviewDashboard />
        </section>

        {/* ── Your Past Interviews ───────────────────────────────────────── */}
        <section style={{ marginBottom: 56 }}>
          <h2 style={{ color: "#fff", fontWeight: 700, fontSize: 24, marginBottom: 24 }}>
            Your Past Interviews
          </h2>
          <div
            style={{
              display: "flex",
              gap: 20,
              overflowX: "auto",
              paddingBottom: 8,
              scrollSnapType: "x mandatory",
            }}
          >
            {pastInterviews.map((iv) => (
              <div key={iv.id} style={{ scrollSnapAlign: "start", flexShrink: 0 }}>
                <InterviewCard interview={iv} />
              </div>
            ))}
          </div>
        </section>

        {/* ── Pick Your Interview ────────────────────────────────────────── */}
        <section>
          <h2 style={{ color: "#fff", fontWeight: 700, fontSize: 24, marginBottom: 24 }}>
            Pick Your Interview
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(270px, 1fr))",
              gap: 20,
            }}
          >
            {availableInterviews.map((iv) => (
              <InterviewCard key={iv.id} interview={iv} />
            ))}
          </div>
        </section>
      </main>
    </div>
  );
};

export default HomePage;
