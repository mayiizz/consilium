import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Logo } from "@/components/brand/Logo";
import { useAuth } from "@/lib/auth-context";
import { formatApiError } from "@/lib/api/client";
import { AVATAR_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { Mic, ListTodo, Bot, Check, Shield, Zap } from "lucide-react";

export const Route = createFileRoute("/auth")({ component: AuthPage });

const VALUE_PROPS = [
  { icon: Mic, title: "Live transcription", desc: "Real-time, searchable forever." },
  { icon: ListTodo, title: "AI task extraction", desc: "Action items on Kanban before the call ends." },
  { icon: Bot, title: "Agentic PM", desc: "Planning, monitoring, and requirements agents." },
];

const TRUST_BADGES = [
  { icon: Check, text: "No card required" },
  { icon: Shield, text: "SOC 2 in progress" },
  { icon: Zap, text: "5-min setup" },
];

const MIN_PASSWORD_LENGTH = 8;

function AuthPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [tab, setTab] = useState<"in" | "up">("in");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [name, setName] = useState("");
  const [rEmail, setREmail] = useState("");
  const [rPassword, setRPassword] = useState("");
  const [role, setRole] = useState<"manager" | "member">("manager");
  const [skills, setSkills] = useState("");
  const [avatar, setAvatar] = useState(AVATAR_OPTIONS[0].url);
  const [busy, setBusy] = useState(false);

  const onSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    setBusy(true);
    try { await login(email, password); toast.success("Welcome back"); navigate({ to: "/business" }); }
    catch (err) { toast.error(formatApiError(err, "Invalid credentials")); } finally { setBusy(false); }
  };

  const onSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !rEmail || !rPassword) return;
    if (rPassword.length < MIN_PASSWORD_LENGTH) {
      toast.error(`Password must be at least ${MIN_PASSWORD_LENGTH} characters`);
      return;
    }
    setBusy(true);
    try {
      await register({ name, email: rEmail, password: rPassword, role, skills: skills.split(",").map((s) => s.trim()).filter(Boolean), avatar });
      toast.success("Account created");
      navigate({ to: "/business" });
    } catch (err) {
      const msg = formatApiError(err, "Could not create account");
      toast.error(msg.includes("already registered") ? `${msg}. Try signing in instead.` : msg);
    } finally { setBusy(false); }
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/60 px-6 py-4">
        <Link to="/"><Logo /></Link>
      </header>
      <div className="relative flex flex-1 overflow-hidden">
        <div className="absolute -top-40 left-1/4 -z-10 h-[500px] w-[700px] rounded-full bg-primary/15 blur-[120px]" />

        {/* Form panel */}
        <div className="flex flex-1 items-center justify-center p-6 lg:p-12">
          <Card className="w-full max-w-md glass-card border-border/60 shadow-elevated">
            <CardHeader className="text-center">
              <h1 className="text-2xl font-bold tracking-tight">Welcome to <span className="gradient-text">Consilium</span></h1>
              <p className="text-sm text-muted-foreground">Sign in or create an account to continue.</p>
            </CardHeader>
            <CardContent>
              <Tabs value={tab} onValueChange={(v) => setTab(v as "in" | "up")}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="in">Sign In</TabsTrigger>
                  <TabsTrigger value="up">Sign Up</TabsTrigger>
                </TabsList>
                <TabsContent value="in">
                  <form onSubmit={onSignIn} className="space-y-4 pt-4">
                    <div className="space-y-1.5">
                      <Label>Email</Label>
                      <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@team.com" />
                    </div>
                    <div className="space-y-1.5">
                      <Label>Password</Label>
                      <Input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
                    </div>
                    <div className="flex justify-end text-xs">
                      <Link to="/forgot-password" className="text-primary hover:underline">Forgot password?</Link>
                    </div>
                    <Button type="submit" disabled={busy} className="w-full gradient-primary rounded-xl">{busy ? "Signing in…" : "Sign In"}</Button>
                  </form>
                </TabsContent>
                <TabsContent value="up">
                  <form onSubmit={onSignUp} className="space-y-4 pt-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <Label>Name</Label>
                        <Input required value={name} onChange={(e) => setName(e.target.value)} />
                      </div>
                      <div className="space-y-1.5">
                        <Label>Email</Label>
                        <Input type="email" required value={rEmail} onChange={(e) => setREmail(e.target.value)} />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <Label>Password</Label>
                      <Input
                        type="password"
                        required
                        minLength={MIN_PASSWORD_LENGTH}
                        value={rPassword}
                        onChange={(e) => setRPassword(e.target.value)}
                        autoComplete="new-password"
                      />
                      <p className="text-xs text-muted-foreground">At least {MIN_PASSWORD_LENGTH} characters</p>
                    </div>
                    <div className="space-y-1.5">
                      <Label>Role</Label>
                      <Select value={role} onValueChange={(v) => setRole(v as "manager" | "member")}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="manager">Manager</SelectItem>
                          <SelectItem value="member">Team Member</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label>Skills (comma-separated)</Label>
                      <Input value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="React, Product, Design" />
                    </div>
                    <div className="space-y-1.5">
                      <Label>Avatar</Label>
                      <div className="grid grid-cols-6 gap-2">
                        {AVATAR_OPTIONS.map((a) => (
                          <button
                            key={a.seed}
                            type="button"
                            onClick={() => setAvatar(a.url)}
                            className={cn("rounded-lg border-2 p-1 transition-all", avatar === a.url ? "border-primary shadow-glow" : "border-transparent hover:border-border")}
                          >
                            <img src={a.url} alt={a.seed} className="h-10 w-10" />
                          </button>
                        ))}
                      </div>
                    </div>
                    <Button type="submit" disabled={busy} className="w-full gradient-primary rounded-xl">{busy ? "Creating…" : "Create account"}</Button>
                  </form>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>

        {/* Value prop panel */}
        <div className="hidden w-[420px] flex-col justify-center border-l border-border/60 bg-muted/30 p-10 lg:flex xl:w-[480px]">
          <h2 className="text-2xl font-bold tracking-tight">Turn meetings into <span className="gradient-text">shipped work</span></h2>
          <p className="mt-2 text-sm text-muted-foreground">Join teams using Consilium to transcribe, extract, and route work automatically.</p>
          <div className="mt-8 space-y-4">
            {VALUE_PROPS.map((v) => (
              <div key={v.title} className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl gradient-primary shadow-glow">
                  <v.icon size={18} className="text-white" />
                </div>
                <div>
                  <div className="font-semibold">{v.title}</div>
                  <div className="text-sm text-muted-foreground">{v.desc}</div>
                </div>
              </div>
            ))}
          </div>
          <blockquote className="mt-8 rounded-xl border border-border/60 bg-background/60 p-4 text-sm italic text-muted-foreground">
            "Cut our standup time in half. Tasks just appear."
            <footer className="mt-2 text-xs font-semibold not-italic text-foreground">— Ada L., Tech Lead</footer>
          </blockquote>
          <div className="mt-6 flex flex-wrap gap-4 text-xs text-muted-foreground">
            {TRUST_BADGES.map((b) => (
              <span key={b.text} className="flex items-center gap-1.5"><b.icon size={14} className="text-success" /> {b.text}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
