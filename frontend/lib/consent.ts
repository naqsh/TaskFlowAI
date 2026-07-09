import { apiFetch } from "@/lib/api";

export type ConsentStatus = {
  granted: boolean;
  scope: string;
  expires_at?: string | null;
};

export type ConsentGrantResponse = {
  status: string;
  scope: string;
  expires_at: string;
};

export async function grantAIConsent(): Promise<ConsentGrantResponse> {
  return apiFetch<ConsentGrantResponse>("/api/v1/consent/ai", {
    method: "POST",
    body: JSON.stringify({ scope: "ai_assistance" }),
  });
}

export async function getAIConsentStatus(): Promise<ConsentStatus> {
  return apiFetch<ConsentStatus>("/api/v1/consent/ai");
}

export async function revokeAIConsent(): Promise<ConsentStatus> {
  return apiFetch<ConsentStatus>("/api/v1/consent/ai", { method: "DELETE" });
}
