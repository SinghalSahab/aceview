/* ==================== TEMPORARY TEST DASHBOARD (START) - DELETE WHEN DONE ==================== */
'use client';

import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Github, 
  Code2, 
  Layers, 
  TestTube2, 
  FileCode, 
  BookOpen, 
  GitCommit, 
  User, 
  Mail, 
  Phone, 
  Building2, 
  Briefcase, 
  Star, 
  GitFork, 
  ExternalLink, 
  Search, 
  Loader2, 
  ChevronDown, 
  ChevronRight,
  Database,
  Sparkles,
  Terminal
} from 'lucide-react';
import { apiFetch } from "@/lib/api";

interface BackendTestDashboardProps {
  data: {
    text?: string;
    fileName?: string;
    fileSize?: number;
    parsed_details?: any;
    github_profile?: any;
    rawResponse?: any;
  } | null;
}

export default function BackendTestDashboard({ data }: BackendTestDashboardProps) {
  const [manualGithubUser, setManualGithubUser] = useState('');
  const [isAnalyzingGithub, setIsAnalyzingGithub] = useState(false);
  const [liveGithubData, setLiveGithubData] = useState<any>(null);
  const [githubError, setGithubError] = useState<string | null>(null);
  const [showRawJson, setShowRawJson] = useState(false);
  const [activeTab, setActiveTab] = useState<'skills' | 'github' | 'validation' | 'raw'>('skills');

  const parsed = data?.parsed_details;
  const github = liveGithubData || data?.github_profile;

  const handleManualGithubAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualGithubUser.trim()) return;

    setIsAnalyzingGithub(true);
    setGithubError(null);

    try {
      const res = await apiFetch(`/api/github/analyze/${encodeURIComponent(manualGithubUser.trim())}`);
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || errJson?.error || `Failed to fetch GitHub profile (Status: ${res.status})`);
      }
      const json = await res.json();
      setLiveGithubData(json);
      setActiveTab('github');
    } catch (err: any) {
      setGithubError(err.message || 'Error fetching GitHub metrics');
    } finally {
      setIsAnalyzingGithub(false);
    }
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'text-neutral-400 border-neutral-600 bg-neutral-800/40';
    if (score >= 75) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
    if (score >= 50) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
    return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
  };

  const getProgressBarColor = (score: number | null | undefined) => {
    if (score === null || score === undefined) return 'bg-neutral-600';
    if (score >= 75) return 'bg-gradient-to-r from-emerald-500 to-teal-400';
    if (score >= 50) return 'bg-gradient-to-r from-amber-500 to-yellow-400';
    return 'bg-gradient-to-r from-rose-500 to-red-400';
  };

  if (!data && !liveGithubData) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-center border border-white/5 bg-[#121220]/40 backdrop-blur-xl rounded-2xl m-4">
        <div className="p-4 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 mb-4">
          <Terminal className="w-8 h-8 animate-pulse" />
        </div>
        <h3 className="text-lg font-semibold text-white">Backend Test Inspector Ready</h3>
        <p className="text-xs text-neutral-400 max-w-md mt-1 mb-6">
          Upload a resume PDF on the left to inspect extracted skills, profile entities, and automated GitHub code quality metrics in real-time.
        </p>

        {/* Manual GitHub Query Form */}
        <form onSubmit={handleManualGithubAnalyze} className="flex items-center gap-2 max-w-md w-full">
          <div className="relative flex-1">
            <Github className="absolute left-3 top-2.5 w-4 h-4 text-neutral-500" />
            <input
              type="text"
              placeholder="Or test a GitHub username (e.g. octocat)..."
              value={manualGithubUser}
              onChange={(e) => setManualGithubUser(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={isAnalyzingGithub}
            className="px-4 py-2 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition duration-200 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            {isAnalyzingGithub ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
            <span>Analyze</span>
          </button>
        </form>
        {githubError && <p className="text-xs text-red-400 mt-2">{githubError}</p>}
      </div>
    );
  }

  const validation = parsed?.validation;

  return (
    <div className="flex flex-col gap-5 p-6 overflow-y-auto max-h-[calc(100vh-8rem)]">
      {/* Top Banner: Candidate & Validation Bar */}
      <div className="border border-white/10 bg-[#131322]/80 backdrop-blur-xl rounded-2xl p-5 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 left-0 w-1.5 h-full bg-gradient-to-b from-purple-500 to-indigo-500" />
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <User className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-bold text-white tracking-tight">
                {parsed?.name || "Extracted Candidate Profile"}
              </h2>
              {validation && (
                <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1 ${
                  validation.status === 'ok' 
                    ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' 
                    : validation.status === 'flagged' 
                    ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' 
                    : 'text-rose-400 border-rose-500/30 bg-rose-500/10'
                }`}>
                  {validation.status === 'ok' && <CheckCircle2 className="w-3 h-3" />}
                  {validation.status === 'flagged' && <AlertTriangle className="w-3 h-3" />}
                  {validation.status === 'failed' && <XCircle className="w-3 h-3" />}
                  <span>Status: {validation.status?.toUpperCase()}</span>
                </span>
              )}
            </div>

            {/* Candidate Metadata Pills */}
            <div className="flex flex-wrap items-center gap-3 mt-3 text-xs text-neutral-400 font-medium">
              {parsed?.years_of_experience !== undefined && parsed?.years_of_experience !== null && (
                <span className="flex items-center gap-1 bg-white/5 px-2.5 py-1 rounded-lg border border-white/5 text-neutral-300">
                  <Briefcase className="w-3.5 h-3.5 text-purple-400" />
                  {parsed.years_of_experience} {parsed.years_of_experience === 1 ? 'Year' : 'Years'} Exp
                </span>
              )}

              {parsed?.emails && parsed.emails.length > 0 && (
                <span className="flex items-center gap-1 bg-white/5 px-2.5 py-1 rounded-lg border border-white/5 text-neutral-300">
                  <Mail className="w-3.5 h-3.5 text-blue-400" />
                  {parsed.emails.join(', ')}
                </span>
              )}

              {parsed?.phones && parsed.phones.length > 0 && (
                <span className="flex items-center gap-1 bg-white/5 px-2.5 py-1 rounded-lg border border-white/5 text-neutral-300">
                  <Phone className="w-3.5 h-3.5 text-emerald-400" />
                  {parsed.phones.join(', ')}
                </span>
              )}

              {parsed?.links?.github && parsed.links.github.length > 0 && (
                <a
                  href={parsed.links.github[0]}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 px-2.5 py-1 rounded-lg border border-purple-500/20 transition-colors"
                >
                  <Github className="w-3.5 h-3.5" />
                  <span>GitHub Profile</span>
                  <ExternalLink className="w-3 h-3 opacity-70" />
                </a>
              )}
            </div>
          </div>

          {/* Quick Stats Box */}
          <div className="flex items-center gap-2 self-start md:self-auto bg-black/30 p-2 rounded-xl border border-white/5 text-center">
            <div className="px-3 py-1">
              <div className="text-xs text-neutral-400">Skills Detected</div>
              <div className="text-base font-bold text-white">{parsed?.skills?.length || 0}</div>
            </div>
            <div className="w-[1px] h-7 bg-white/10" />
            <div className="px-3 py-1">
              <div className="text-xs text-neutral-400">Code Score</div>
              <div className={`text-base font-bold ${getScoreColor(github?.general?.aggregate_score).split(' ')[0]}`}>
                {github?.general?.aggregate_score !== null && github?.general?.aggregate_score !== undefined
                  ? `${github.general.aggregate_score}/100` 
                  : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-white/10 pb-3">
        <button
          onClick={() => setActiveTab('skills')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
            activeTab === 'skills'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Skills & Resume Entities ({parsed?.skills?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('github')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
            activeTab === 'github'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white'
          }`}
        >
          <Github className="w-3.5 h-3.5" />
          <span>GitHub Discovery & Code Metrics ({github?.general?.repos?.length || 0} Repos)</span>
        </button>

        <button
          onClick={() => setActiveTab('validation')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
            activeTab === 'validation'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
              : 'bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Validation Issues ({validation?.issues?.length || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab('raw')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ml-auto ${
            activeTab === 'raw'
              ? 'bg-neutral-700 text-white'
              : 'bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white'
          }`}
        >
          <Code2 className="w-3.5 h-3.5" />
          <span>Raw JSON Payload</span>
        </button>
      </div>

      {/* TAB 1: Skills & Extracted Details */}
      {activeTab === 'skills' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left Column: Skills Badges */}
          <div className="lg:col-span-2 border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Code2 className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Extracted Skills (spaCy NER & Pattern Match)</h3>
              </div>
              <span className="text-xs text-neutral-500 font-mono">{parsed?.skills?.length || 0} normalized skills</span>
            </div>

            {parsed?.skills && parsed.skills.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {parsed.skills.map((skill: string, idx: number) => (
                  <span 
                    key={idx} 
                    className="text-xs font-medium bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/25 px-3 py-1 rounded-lg transition-colors shadow-sm"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-neutral-500 italic">No skills extracted from this document.</p>
            )}

            {/* Organizations / Companies */}
            <div className="mt-6 pt-5 border-t border-white/5">
              <div className="flex items-center gap-2 mb-3">
                <Building2 className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-white">Detected Organizations</h3>
              </div>
              {parsed?.organizations && parsed.organizations.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {parsed.organizations.map((org: string, idx: number) => (
                    <span 
                      key={idx} 
                      className="text-xs font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20 px-2.5 py-1 rounded-lg"
                    >
                      {org}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-neutral-500 italic">No organizations detected.</p>
              )}
            </div>
          </div>

          {/* Right Column: Detected Sections & Links */}
          <div className="flex flex-col gap-4">
            {/* Sections Found */}
            <div className="border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-white">Resume Sections</h3>
              </div>
              <div className="flex flex-col gap-1.5">
                {parsed?.sections ? (
                  Object.keys(parsed.sections).map((secKey) => (
                    <div key={secKey} className="flex items-center justify-between text-xs py-1 px-2 rounded bg-white/5 text-neutral-300">
                      <span className="font-mono text-purple-300">{secKey}</span>
                      <span className="text-[10px] text-neutral-500">{parsed.sections[secKey]?.length || 0} chars</span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-neutral-500 italic">No section structure detected.</p>
                )}
              </div>
            </div>

            {/* Projects with links */}
            <div className="border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Briefcase className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Project Links</h3>
              </div>
              {parsed?.links?.projects && parsed.links.projects.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {parsed.links.projects.map((proj: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-xs">
                      <div className="font-semibold text-white truncate">{proj.project || `Project #${idx + 1}`}</div>
                      {proj.github && (
                        <a 
                          href={proj.github} 
                          target="_blank" 
                          rel="noreferrer"
                          className="flex items-center gap-1 text-purple-400 hover:text-purple-300 text-[11px] mt-1 truncate"
                        >
                          <Github className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{proj.github}</span>
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-neutral-500 italic">No project links resolved.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: GitHub Discovery & Code Quality Metrics */}
      {activeTab === 'github' && (
        <div className="flex flex-col gap-5">
          {/* Live GitHub Query Bar */}
          <div className="border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-neutral-300">
              <Github className="w-4 h-4 text-purple-400" />
              <span>Current GitHub Target:</span>
              <span className="font-mono text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">
                {github?.username || "Not Linked"}
              </span>
            </div>

            <form onSubmit={handleManualGithubAnalyze} className="flex items-center gap-2 w-full sm:w-auto">
              <input
                type="text"
                placeholder="Test any username..."
                value={manualGithubUser}
                onChange={(e) => setManualGithubUser(e.target.value)}
                className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 rounded-xl text-white placeholder-neutral-500 focus:outline-none focus:border-purple-500 transition-colors w-48"
              />
              <button
                type="submit"
                disabled={isAnalyzingGithub}
                className="px-3 py-1.5 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition duration-200 flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
              >
                {isAnalyzingGithub ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}
                <span>Fetch Metrics</span>
              </button>
            </form>
          </div>

          {/* Aggregate Quality Score Card */}
          {github?.general ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Main Overall Code Score Widget */}
              <div className="border border-white/10 bg-gradient-to-br from-[#18182d] to-[#121220] backdrop-blur-xl rounded-2xl p-6 flex flex-col justify-between shadow-xl">
                <div>
                  <span className="text-xs uppercase font-bold text-neutral-400 tracking-wider">Candidate Code Quality</span>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className={`text-4xl font-extrabold ${getScoreColor(github.general.aggregate_score).split(' ')[0]}`}>
                      {github.general.aggregate_score !== null && github.general.aggregate_score !== undefined
                        ? github.general.aggregate_score 
                        : '--'}
                    </span>
                    <span className="text-sm font-semibold text-neutral-500">/ 100</span>
                  </div>
                  <p className="text-xs text-neutral-400 mt-2">
                    Relevance-weighted composite score across top {github.general.repos?.length || 0} public repositories.
                  </p>
                </div>

                <div className="w-full bg-white/5 rounded-full h-2 mt-4 overflow-hidden">
                  <div 
                    className={`h-full rounded-full ${getProgressBarColor(github.general.aggregate_score)}`} 
                    style={{ width: `${Math.min(100, Math.max(0, github.general.aggregate_score || 0))}%` }}
                  />
                </div>
              </div>

              {/* Repositories Scored breakdown list */}
              <div className="md:col-span-2 border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-6">
                <h4 className="text-xs uppercase font-bold text-neutral-400 tracking-wider mb-3">Top Discovered Repositories</h4>
                <div className="flex flex-col gap-3">
                  {github.general.repos && github.general.repos.length > 0 ? (
                    github.general.repos.map((repo: any, idx: number) => (
                      <div key={idx} className="border border-white/5 bg-black/20 rounded-xl p-3.5 flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2 min-w-0">
                            <Code2 className="w-4 h-4 text-purple-400 flex-shrink-0" />
                            <span className="text-xs font-semibold text-white truncate">{repo.name}</span>
                            <span className="text-[10px] text-neutral-500 font-mono">
                              Relevance: {(repo.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getScoreColor(repo.overall_code_score)}`}>
                            {repo.overall_code_score}/100
                          </span>
                        </div>

                        {/* Metric Sub-bars */}
                        <div className="grid grid-cols-5 gap-2 mt-1 pt-2 border-t border-white/5 text-[10px] text-neutral-400 text-center">
                          <div className="bg-white/5 p-1 rounded">
                            <div>Arch</div>
                            <div className="font-bold text-white">{repo.architecture_score}</div>
                          </div>
                          <div className="bg-white/5 p-1 rounded">
                            <div>Test</div>
                            <div className="font-bold text-white">{repo.testing_score}</div>
                          </div>
                          <div className="bg-white/5 p-1 rounded">
                            <div>Complex</div>
                            <div className="font-bold text-white">{repo.complexity_score}</div>
                          </div>
                          <div className="bg-white/5 p-1 rounded">
                            <div>Docs</div>
                            <div className="font-bold text-white">{repo.documentation_score}</div>
                          </div>
                          <div className="bg-white/5 p-1 rounded">
                            <div>Commits</div>
                            <div className="font-bold text-white">{repo.commit_score}</div>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-neutral-500 italic">No public repositories discovered or analyzed.</p>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center border border-white/5 bg-[#131322]/40 rounded-2xl">
              <Github className="w-8 h-8 text-neutral-500 mx-auto mb-2" />
              <p className="text-xs text-neutral-400">No GitHub profile linked on the resume. Use the search input above to test a GitHub username directly.</p>
            </div>
          )}

          {/* Project-Specific Analyzed Repositories */}
          {github?.project_specific?.projects && github.project_specific.projects.length > 0 && (
            <div className="border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-6">
              <h4 className="text-xs uppercase font-bold text-neutral-400 tracking-wider mb-3">
                Project-Specific Resolved Repositories (Independent Analysis)
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {github.project_specific.projects.map((proj: any, idx: number) => (
                  <div key={idx} className="border border-white/5 bg-black/20 rounded-xl p-4 flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="text-xs font-bold text-white truncate">{proj.project_name}</span>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded border ${getScoreColor(proj.overall_code_score)}`}>
                          {proj.overall_code_score}/100
                        </span>
                      </div>
                      <p className="text-[11px] text-purple-300 font-mono mb-3 truncate">{proj.repo_full_name}</p>
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-neutral-400 pt-2 border-t border-white/5">
                      <span>Files: {proj.files_analyzed || 0}</span>
                      <span>Total LOC: {proj.total_loc_analyzed?.toLocaleString() || 0}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Validation Issues */}
      {activeTab === 'validation' && (
        <div className="border border-white/10 bg-[#131322]/60 backdrop-blur-xl rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-semibold text-white">Resume Parsing Validation Audit</h3>
          </div>

          {validation?.issues && validation.issues.length > 0 ? (
            <div className="flex flex-col gap-2.5">
              {validation.issues.map((issue: string, idx: number) => (
                <div key={idx} className="flex items-start gap-3 p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs text-amber-200">
                  <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                  <span>{issue}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-2 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300">
              <CheckCircle2 className="w-4 h-4" />
              <span>All validation checks passed with zero critical flags!</span>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: Raw JSON Explorer */}
      {activeTab === 'raw' && (
        <div className="border border-white/10 bg-black/50 backdrop-blur-xl rounded-2xl p-4">
          <div className="flex items-center justify-between mb-2 pb-2 border-b border-white/10">
            <span className="text-xs font-mono text-neutral-400">Complete FastAPI JSON Payload</span>
            <button 
              onClick={() => navigator.clipboard.writeText(JSON.stringify(data?.rawResponse || data, null, 2))}
              className="text-[11px] bg-white/10 hover:bg-white/20 text-white px-2.5 py-1 rounded transition cursor-pointer"
            >
              Copy JSON
            </button>
          </div>
          <pre className="text-[11px] text-neutral-300 font-mono max-h-[500px] overflow-y-auto p-3 rounded-xl bg-[#09090f] select-all leading-relaxed whitespace-pre-wrap">
            {JSON.stringify(data?.rawResponse || data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// Small icon helper
function ShieldAlert(props: any) {
  return <AlertTriangle {...props} />;
}
/* ==================== TEMPORARY TEST DASHBOARD (END) ==================== */
