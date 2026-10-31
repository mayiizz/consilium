import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Logo } from "@/components/brand/Logo";
import { useAuth } from "@/lib/auth-context";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/profile")({ component: Page });

function Page() {
  const { user, isLoading, updateUser } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [skills, setSkills] = useState("");

  useEffect(() => {
    if (!isLoading && !user) navigate({ to: "/auth" });
    if (user) { setName(user.name); setSkills(user.skills.join(", ")); }
  }, [user, isLoading, navigate]);

  if (!user) return null;

  const save = () => {
    updateUser({ name, skills: skills.split(",").map((s) => s.trim()).filter(Boolean) });
    toast.success("Profile updated");
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border/60 px-6">
        <Link to="/"><Logo /></Link>
        <Button variant="ghost" size="sm" className="ml-auto" onClick={() => navigate({ to: "/business" })}>
          <ArrowLeft size={14} /> Back to dashboard
        </Button>
      </header>
      <div className="mx-auto max-w-3xl p-6">
        <h1 className="mb-6 text-3xl font-bold tracking-tight">Profile</h1>
        <Card className="glass-card">
          <CardHeader>
            <div className="flex items-center gap-4">
              <Avatar className="h-16 w-16 ring-2 ring-primary/30"><AvatarImage src={user.avatar} /><AvatarFallback>{user.name[0]}</AvatarFallback></Avatar>
              <div>
                <div className="text-lg font-semibold">{user.name}</div>
                <div className="text-sm text-muted-foreground">{user.email}</div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5"><Label>Display name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Skills (comma-separated)</Label><Input value={skills} onChange={(e) => setSkills(e.target.value)} /></div>
            <Button onClick={save} className="gradient-primary rounded-xl">Save changes</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
