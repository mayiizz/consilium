import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/brand/Logo";
import { toast } from "sonner";

export const Route = createFileRoute("/reset-password")({ component: Page });

function Page() {
  const navigate = useNavigate();
  const [pw, setPw] = useState("");
  const [c, setC] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (pw !== c) return toast.error("Passwords don't match");
    toast.success("Password updated. Please sign in.");
    navigate({ to: "/auth" });
  };
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/60 px-6 py-4"><Link to="/"><Logo /></Link></header>
      <div className="flex flex-1 items-center justify-center p-6">
        <Card className="w-full max-w-md glass-card shadow-elevated">
          <CardHeader>
            <h1 className="text-2xl font-bold tracking-tight">Set a new password</h1>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <div className="space-y-1.5"><Label>New password</Label><Input type="password" required value={pw} onChange={(e) => setPw(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Confirm password</Label><Input type="password" required value={c} onChange={(e) => setC(e.target.value)} /></div>
              <Button type="submit" className="w-full gradient-primary rounded-xl">Update password</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
