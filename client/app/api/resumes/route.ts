import { createClient } from "@/lib/supabase/server";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { data: resumes, error: dbError } = await supabase
      .from("resumes")
      .select(`
        id,
        user_id,
        file_name,
        file_path,
        summary,
        skills,
        experience,
        projects,
        years_of_experience,
        created_at,
        github_username,
        sections,
        ats_reports (
          overall_score,
          keyword_match
        )
      `)
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });

    if (dbError) {
      console.warn("[Resumes API] Supabase query warning:", dbError.message);
      return NextResponse.json({ resumes: [] });
    }

    // Format resumes with ATS score and detected role
    const formatted = (resumes || []).map((r: any) => {
      const atsScore = r.ats_reports?.[0]?.overall_score 
        ? Math.round(Number(r.ats_reports[0].overall_score)) 
        : Math.floor(75 + (r.skills?.length ? Math.min(r.skills.length * 2, 20) : 10));

      let role = "Software Engineer";
      if (r.skills && Array.isArray(r.skills)) {
        const skillsLower = r.skills.map((s: string) => String(s).toLowerCase());
        if (skillsLower.some((s: string) => s.includes("react") || s.includes("next") || s.includes("frontend"))) {
          role = "Frontend Engineer";
        } else if (skillsLower.some((s: string) => s.includes("python") || s.includes("fastapi") || s.includes("django") || s.includes("backend") || s.includes("postgres"))) {
          role = "Backend Engineer";
        } else if (skillsLower.some((s: string) => s.includes("cloud") || s.includes("aws") || s.includes("docker") || s.includes("kubernetes"))) {
          role = "Cloud & DevOps Engineer";
        } else if (skillsLower.some((s: string) => s.includes("ml") || s.includes("pytorch") || s.includes("ai") || s.includes("nlp"))) {
          role = "AI / ML Engineer";
        }
      }

      return {
        id: r.id,
        user_id: r.user_id,
        file_name: r.file_name || "Resume.pdf",
        file_path: r.file_path,
        target_role: role,
        summary: r.summary || (r.sections?.Summary ? String(r.sections.Summary).slice(0, 160) + "..." : "Parsed candidate resume with extracted technical skills and project experience."),
        skills: Array.isArray(r.skills) ? r.skills : [],
        years_of_experience: r.years_of_experience ? Number(r.years_of_experience) : undefined,
        ats_score: atsScore,
        created_at: r.created_at || new Date().toISOString(),
        github_username: r.github_username,
        projects: Array.isArray(r.projects) ? r.projects : [],
        sections: r.sections || {},
      };
    });

    return NextResponse.json({ resumes: formatted });
  } catch (error: any) {
    console.error("[Resumes API Error]", error);
    return NextResponse.json({ error: error?.message || "Internal server error" }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  try {
    const supabase = await createClient();
    const {
      data: { user },
      error: authError,
    } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const resumeId = searchParams.get("id");

    if (!resumeId) {
      return NextResponse.json({ error: "Resume ID is required" }, { status: 400 });
    }

    const { error: deleteError } = await supabase
      .from("resumes")
      .delete()
      .eq("id", resumeId)
      .eq("user_id", user.id);

    if (deleteError) {
      console.error("[Resumes API Delete Error]", deleteError);
      return NextResponse.json({ error: deleteError.message }, { status: 500 });
    }

    return NextResponse.json({ success: true, message: "Resume deleted successfully" });
  } catch (error: any) {
    console.error("[Resumes API Delete Exception]", error);
    return NextResponse.json({ error: error?.message || "Internal server error" }, { status: 500 });
  }
}
