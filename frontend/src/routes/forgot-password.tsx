import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Logo } from "@/components/brand/Logo";
import { toast } from "sonner";

export const Route = createFileRoute("/forgot-password")({ component: Page });

function Page() {
  const [email, setEmail] = useState("");
  const submit = (e: React.FormEvent) => { e.preventDefault(); toast.success("If an account exists, a reset link has been sent."); };
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/60 px-6 py-4"><Link to="/"><Logo /></Link></header>
      <div className="flex flex-1 items-center justify-center p-6">
        <Card className="w-full max-w-md glass-card shadow-elevated">
          <CardHeader>
            <h1 className="text-2xl font-bold tracking-tight">Reset your password</h1>
            <p className="text-sm text-muted-foreground">Enter your email and we'll send you a reset link.</p>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4">
              <div className="space-y-1.5">
                <Label>Email</Label>
                <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <Button type="submit" className="w-full gradient-primary rounded-xl">Send reset link</Button>
              <div className="text-center text-sm"><Link to="/auth" className="text-primary hover:underline">Back to sign in</Link></div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
