import { createFileRoute } from "@tanstack/react-router";
import { Link, useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/lib/auth-context";
import { Logo } from "@/components/brand/Logo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Mic, ListTodo, TrendingUp, GitBranch, Bot, FileText, Sparkles, ArrowRight,
  Check, Zap, Shield, LogOut, UserIcon, Video, MessageSquare, Github,
} from "lucide-react";
import {
  Accordion, AccordionContent, AccordionItem, AccordionTrigger,
} from "@/components/ui/accordion";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "CONSILIUM — Turn meetings into shipped work" },
      { name: "description", content: "AI project intelligence: live transcription, automatic task extraction, Kanban, GitHub sync, and agentic project management." },
      { property: "og:title", content: "CONSILIUM — AI Project Intelligence" },
      { property: "og:description", content: "Turn meetings into shipped work. Live transcription, task extraction, Kanban, and agentic PM." },
    ],
  }),
  component: LandingPage,
});

const FEATURES = [
  { icon: Mic, title: "Live Transcription", desc: "Real-time transcription. Searchable forever." },
  { icon: ListTodo, title: "AI Task Extraction", desc: "Action items appear on your Kanban before the call ends." },
  { icon: GitBranch, title: "GitHub Sync", desc: "Two-way bridge between meetings, tasks, and pull requests." },
  { icon: Bot, title: "Agentic PM", desc: "Planning, Monitoring, and Requirements agents work for you." },
  { icon: FileText, title: "PRDs in Minutes", desc: "Generate, edit, and ship PRDs from a single conversation." },
  { icon: TrendingUp, title: "Risk Radar", desc: "Surface blockers and slipping work the moment they appear." },
];

const TIERS = [
  { name: "Starter", price: "$0", period: "/forever", features: ["1 workspace", "5 meetings / mo", "Basic Kanban"], cta: "Start free", featured: false },
  { name: "Pro", price: "$29", period: "/user / mo", features: ["Unlimited meetings", "All AI agents", "GitHub & Slack", "Priority support"], cta: "Try Pro free", featured: true },
  { name: "Enterprise", price: "Custom", period: "", features: ["SSO + SAML", "Audit logs", "Private VPC", "Dedicated CSM"], cta: "Contact sales", featured: false },
];

const TESTIMONIALS = [
  { quote: "Cut our standup time in half. Tasks just appear.", author: "Ada L.", role: "Tech Lead, Helios" },
  { quote: "The PRD agent saved me 6 hours this week.", author: "Ivy R.", role: "PM, Acme" },
  { quote: "Finally — meetings that ship code.", author: "Leo C.", role: "Frontend Eng, Northstar" },
];

const HOW_IT_WORKS = [
  { step: "01", title: "Capture the meeting", desc: "Go live with labeled mic transcript, or upload a text transcript. Consilium runs RAG and automates Kanban." },
  { step: "02", title: "AI extracts the work", desc: "Planning Agent pulls action items, decisions, and risks before the call ends." },
  { step: "03", title: "Ship on Kanban", desc: "Tasks land on your board with assignees, priorities, and GitHub PR links — ready to move." },
];

const INTEGRATIONS = [
  { icon: Github, name: "GitHub", desc: "Two-way sync between meetings, tasks, and pull requests." },
  { icon: MessageSquare, name: "Slack", desc: "Post meeting summaries and task updates to your channels." },
  { icon: Video, name: "Jitsi", desc: "Built-in video calls with live transcription overlay." },
];

const STATS = [
  { value: "12k+", label: "Meetings transcribed" },
  { value: "40%", label: "Faster standups" },
  { value: "6.2h", label: "Saved per PM / week" },
  { value: "98%", label: "Task extraction accuracy" },
];

const FAQ = [
  { q: "Is Consilium free to start?", a: "Yes. The Starter plan is free forever with 1 workspace and 5 meetings per month. Upgrade when your team needs unlimited meetings and full agent access." },
  { q: "How does AI task extraction work?", a: "Our Planning Agent listens to live transcripts, identifies commitments and action items, and routes them to Kanban with suggested assignees based on skills and workload." },
  { q: "Is my meeting data secure?", a: "All data is encrypted in transit and at rest. We're SOC 2 Type II in progress. Enterprise plans include private VPC deployment and audit logs." },
  { q: "Can I connect my existing GitHub repos?", a: "Yes. GitHub integration supports OAuth, two-way PR sync, and CI status monitoring via the Monitoring Agent." },
  { q: "What agents are included?", a: "Planning, Monitoring, and Requirements agents are included on Pro. Routing Agent and custom agent configs are available on Enterprise." },
  { q: "How long is data retained?", a: "Transcripts and meeting data are retained for 12 months on Starter, unlimited on Pro and Enterprise. You can export or delete at any time." },
];

function LandingPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <header className="glass sticky top-0 z-40">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <Logo />
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#pricing" className="hover:text-foreground">Pricing</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/business" })}>
                  Open Dashboard
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger>
                    <Avatar className="h-9 w-9 ring-2 ring-primary/20">
                      <AvatarImage src={user.avatar} />
                      <AvatarFallback>{user.name?.[0]}</AvatarFallback>
                    </Avatar>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => navigate({ to: "/profile" })}>
                      <UserIcon size={14} /> Profile
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => { logout(); }}>
                      <LogOut size={14} /> Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={() => navigate({ to: "/auth" })}>Sign in</Button>
                <Button size="sm" className="gradient-primary rounded-xl" onClick={() => navigate({ to: "/auth" })}>
                  Sign up <ArrowRight size={14} />
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden px-6 py-20 md:py-28">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-40 left-1/2 h-[600px] w-[800px] -translate-x-1/2 rounded-full bg-primary/20 blur-[120px]" />
          <div className="absolute top-40 right-0 h-[400px] w-[500px] rounded-full bg-secondary/20 blur-[120px]" />
        </div>
        <div className="mx-auto grid max-w-7xl items-center gap-12 md:grid-cols-2">
          <div className="animate-fade-in">
            <Badge variant="outline" className="mb-5 gap-1.5 rounded-full border-primary/30 bg-primary/10 py-1 text-primary">
              <Sparkles size={12} /> Now with Agentic PRD generation
            </Badge>
            <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">
              Turn meetings into <span className="gradient-text">shipped work.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted-foreground">
              Consilium listens, transcribes, extracts action items, and routes them straight to your Kanban — with a fleet of AI agents for planning, monitoring, and risk.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button size="lg" className="gradient-primary rounded-xl shadow-glow" onClick={() => navigate({ to: "/auth" })}>
                Start free <ArrowRight size={16} />
              </Button>
              <Button size="lg" variant="outline" className="rounded-xl">
                Watch demo
              </Button>
            </div>
            <div className="mt-8 flex items-center gap-6 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5"><Check size={14} className="text-success" /> No card required</span>
              <span className="flex items-center gap-1.5"><Shield size={14} className="text-success" /> SOC 2 in progress</span>
              <span className="flex items-center gap-1.5"><Zap size={14} className="text-success" /> 5-min setup</span>
            </div>
          </div>

          {/* Live transcript preview */}
          <div className="relative animate-fade-in [animation-delay:120ms]">
            <div
              className="glass-card rounded-3xl p-5 shadow-elevated"
              style={{ transform: "perspective(1200px) rotateY(-8deg) rotateX(4deg)" }}
            >
              <div className="mb-4 flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-success" />
                </span>
                <span className="text-xs font-semibold uppercase tracking-wider text-success">Live · Q4 Planning</span>
                <span className="ml-auto font-mono text-xs tabular-nums text-muted-foreground">14:32</span>
              </div>
              <div className="space-y-3 text-sm">
                {[
                  { s: "Ada", c: "Let's start with the OAuth flow — Leo, where are we?", color: "from-indigo-500 to-purple-500" },
                  { s: "Leo", c: "Passing CI. Need one more review and we merge.", color: "from-fuchsia-500 to-pink-500" },
                  { s: "Maya", c: "Pushed redesigned connect screen to Figma.", color: "from-amber-500 to-orange-500" },
                  { s: "Ada", c: "Action item: race condition in task extractor.", color: "from-indigo-500 to-purple-500" },
                ].map((m, i) => (
                  <div key={i} className="flex gap-2.5">
                    <div className={`h-7 w-7 shrink-0 rounded-full bg-gradient-to-br ${m.color} text-[10px] font-bold text-white grid place-items-center`}>{m.s[0]}</div>
                    <div>
                      <div className="text-[11px] font-semibold text-muted-foreground">{m.s}</div>
                      <div>{m.c}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-4 rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs">
                <div className="mb-1 flex items-center gap-1.5 font-semibold text-primary">
                  <Sparkles size={12} /> 2 tasks extracted
                </div>
                <div className="text-muted-foreground">"Fix race condition" · "Get final review on PR #124"</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-y border-border/60 bg-muted/30 px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">How it works</h2>
            <p className="mt-3 text-muted-foreground">From conversation to shipped work in three steps.</p>
          </div>
          <div className="grid gap-8 md:grid-cols-3">
            {HOW_IT_WORKS.map((s) => (
              <div key={s.step} className="relative text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl gradient-primary text-lg font-extrabold text-white shadow-glow">{s.step}</div>
                <h3 className="text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="px-6 py-16">
        <div className="mx-auto grid max-w-7xl gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {STATS.map((s) => (
            <div key={s.label} className="glass-card rounded-2xl p-6 text-center">
              <div className="text-4xl font-extrabold tracking-tight gradient-text">{s.value}</div>
              <div className="mt-1 text-sm text-muted-foreground">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Everything between "we should…" and "shipped."</h2>
            <p className="mt-3 text-muted-foreground">A unified workspace for meetings, work, and the agents that connect them.</p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="glass-card hover-lift rounded-2xl p-6">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl gradient-primary shadow-glow">
                  <f.icon size={20} className="text-white" />
                </div>
                <h3 className="text-lg font-semibold">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Integrations */}
      <section className="border-y border-border/60 bg-muted/30 px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Works where your team already is</h2>
            <p className="mt-3 text-muted-foreground">Connect Consilium to the tools you use every day.</p>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {INTEGRATIONS.map((i) => (
              <div key={i.name} className="glass-card hover-lift rounded-2xl p-6 text-center">
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl gradient-primary shadow-glow">
                  <i.icon size={22} className="text-white" />
                </div>
                <h3 className="text-lg font-semibold">{i.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{i.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <div className="mx-auto mb-12 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Simple pricing. Real outcomes.</h2>
            <p className="mt-3 text-muted-foreground">Start free. Upgrade when your team feels the lift.</p>
          </div>
          <div className="grid gap-5 md:grid-cols-3">
            {TIERS.map((t) => (
              <div
                key={t.name}
                className={`rounded-3xl p-7 ${t.featured ? "gradient-primary text-white shadow-glow" : "glass-card"}`}
              >
                <div className={`text-sm font-bold uppercase tracking-wider ${t.featured ? "text-white/80" : "text-muted-foreground"}`}>{t.name}</div>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-4xl font-extrabold tracking-tight">{t.price}</span>
                  <span className={`text-sm ${t.featured ? "text-white/80" : "text-muted-foreground"}`}>{t.period}</span>
                </div>
                <ul className="mt-6 space-y-2 text-sm">
                  {t.features.map((f) => (
                    <li key={f} className="flex items-center gap-2">
                      <Check size={14} className={t.featured ? "text-white" : "text-success"} /> {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className={`mt-6 w-full rounded-xl ${t.featured ? "bg-white text-primary hover:bg-white/90" : ""}`}
                  variant={t.featured ? "default" : "outline"}
                  onClick={() => navigate({ to: "/auth" })}
                >
                  {t.cta}
                </Button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="px-6 py-20">
        <div className="mx-auto max-w-7xl">
          <h2 className="mb-12 text-center text-3xl font-bold tracking-tight md:text-4xl">Teams that ship faster.</h2>
          <div className="grid gap-5 md:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <div key={t.author} className="glass-card rounded-2xl p-6">
                <p className="text-base leading-relaxed">"{t.quote}"</p>
                <div className="mt-4 text-sm">
                  <div className="font-semibold">{t.author}</div>
                  <div className="text-muted-foreground">{t.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section id="faq" className="px-6 py-20">
        <div className="mx-auto max-w-3xl">
          <h2 className="mb-8 text-center text-3xl font-bold tracking-tight md:text-4xl">Frequently asked questions</h2>
          <Accordion type="single" collapsible className="space-y-2">
            {FAQ.map((f, i) => (
              <AccordionItem key={f.q} value={`faq-${i}`} className="glass-card rounded-xl border border-border/60 px-4">
                <AccordionTrigger className="text-left font-semibold hover:no-underline">{f.q}</AccordionTrigger>
                <AccordionContent className="text-muted-foreground">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-20">
        <div className="mx-auto max-w-4xl rounded-3xl gradient-primary p-10 text-center text-white shadow-glow md:p-14">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Ready to turn meetings into momentum?</h2>
          <p className="mx-auto mt-3 max-w-lg text-white/80">Join teams shipping faster with AI-powered project intelligence. Free to start — no credit card required.</p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button size="lg" className="rounded-xl bg-white text-primary hover:bg-white/90" onClick={() => navigate({ to: "/auth" })}>
              Start free <ArrowRight size={16} />
            </Button>
            <Button size="lg" variant="outline" className="rounded-xl border-white/40 bg-transparent text-white hover:bg-white/10" onClick={() => navigate({ to: "/auth" })}>
              Talk to sales
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 px-6 py-12">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-8 md:grid-cols-4">
            <div>
              <Logo size="sm" />
              <p className="mt-3 text-sm text-muted-foreground">AI project intelligence for teams that ship.</p>
            </div>
            <div>
              <h4 className="mb-3 text-sm font-semibold">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground">Features</a></li>
                <li><a href="#pricing" className="hover:text-foreground">Pricing</a></li>
                <li><a href="#faq" className="hover:text-foreground">FAQ</a></li>
              </ul>
            </div>
            <div>
              <h4 className="mb-3 text-sm font-semibold">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="mailto:hello@consilium.ai" className="hover:text-foreground">Contact</a></li>
                <li><Link to="/" className="hover:text-foreground">About</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="mb-3 text-sm font-semibold">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><Link to="/" className="hover:text-foreground">Privacy</Link></li>
                <li><Link to="/" className="hover:text-foreground">Terms</Link></li>
              </ul>
            </div>
          </div>
          <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-border/60 pt-6 text-sm text-muted-foreground">
            <div>© {new Date().getFullYear()} Consilium. All rights reserved.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
