import { Section, Demo } from "./shared";
import { Alert } from "../components/ui/Alert";
import { Progress } from "../components/ui/Progress";
import { Spinner } from "../components/ui/Spinner";
import { Skeleton } from "../components/ui/Skeleton";
import { ToastViewport } from "../components/ui/Toast";
import { useToasts } from "../lib/useToasts";
import { Button } from "../components/ui/Button";

const TOAST_TONES = [
  { tone: "success", title: "Changes saved", description: "Your workspace has been updated." },
  { tone: "danger", title: "Upload failed", description: "The file exceeds the 10 MB limit." },
  { tone: "info", title: "New version available", description: "Refresh to get the latest components." },
];

export function FeedbackSection() {
  const { toasts, push, dismiss } = useToasts();

  return (
    <Section
      id="feedback"
      title="Feedback"
      description="Alerts, toasts, progress bars, spinners, at skeletons — para alam ng user ang nangyayari."
    >
      <Demo label="Alerts — 4 tones, dismissible">
        <div className="flex w-full flex-col gap-3">
          <Alert tone="info" title="Heads up">
            A new version of the design system is available.
          </Alert>
          <Alert tone="success" title="All good">
            Your changes were saved successfully.
          </Alert>
          <Alert tone="warning" title="Storage almost full">
            You've used 92% of your workspace storage.
          </Alert>
          <Alert tone="danger" title="Payment failed" onDismiss={() => {}}>
            We couldn't charge your card. Please update your billing details.
          </Alert>
        </div>
      </Demo>

      <Demo label="Toasts — click to trigger">
        {TOAST_TONES.map((t) => (
          <Button
            key={t.tone}
            variant={t.tone === "danger" ? "destructive" : t.tone === "success" ? "primary" : "outline"}
            onClick={() => push(t)}
          >
            {t.title}
          </Button>
        ))}
        <ToastViewport toasts={toasts} onDismiss={dismiss} />
      </Demo>

      <Demo label="Progress" className="w-full">
        <div className="flex w-full flex-col gap-4">
          <Progress value={25} showLabel />
          <Progress value={60} showLabel />
          <Progress value={90} tone="success" showLabel />
          <Progress value={70} tone="warning" />
          <Progress value={45} tone="danger" />
          <Progress value={55} tone="info" size="lg" />
          <Progress indeterminate />
        </div>
      </Demo>

      <Demo label="Spinner & Skeleton">
        <div className="flex items-center gap-6">
          <Spinner size={16} />
          <Spinner size={20} />
          <Spinner size={28} />
          <Spinner size={36} />
        </div>
        <div className="flex w-full max-w-xs flex-col gap-3">
          <div className="flex items-center gap-3">
            <Skeleton className="size-10 rounded-full" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-3 w-3/4" />
            </div>
          </div>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      </Demo>
    </Section>
  );
}
