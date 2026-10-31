import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/brand/Logo";
import { useAuth } from "@/lib/auth-context";
import { Crown, Users } from "lucide-react";

export const Route = createFileRoute("/business/")({ component: Page });

function Page() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user?.role) return;
    const path =
      user.role === "manager" ? "/business/manager/workspaces" : "/business/member/workspaces";
    navigate({ to: path });
  }, [user, navigate]);

  if (!user) return null;
  if (user.role) return null;

  const pick = (role: "manager" | "member") => {
    updateUser({ role });
    navigate({
      to: role === "manager" ? "/business/manager/workspaces" : "/business/member/workspaces",
    });
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="glass sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-border/60 px-6">
        <Link to="/">
          <Logo />
        </Link>
      </header>
      <div className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-bold tracking-tight">
            Welcome, <span className="gradient-text">{user.name}</span>
          </h1>
          <p className="mt-2 text-muted-foreground">How will you use Consilium?</p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          <Card className="glass-card hover-lift cursor-pointer p-8" onClick={() => pick("manager")}>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl gradient-primary shadow-glow">
              <Crown size={22} className="text-white" />
            </div>
            <h3 className="text-xl font-bold">I'm a Manager</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Run meetings, ship PRDs, manage roadmap and risks across your team.
            </p>
            <Button className="mt-5 w-full gradient-primary rounded-xl">Continue as Manager</Button>
          </Card>
          <Card className="glass-card hover-lift cursor-pointer p-8" onClick={() => pick("member")}>
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-secondary shadow-glow">
              <Users size={22} className="text-white" />
            </div>
            <h3 className="text-xl font-bold">I'm a Team Member</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Join a workspace, see your tasks, and contribute to meetings.
            </p>
            <Button variant="outline" className="mt-5 w-full rounded-xl">
              Continue as Member
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
}
