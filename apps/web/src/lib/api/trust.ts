export type TrustStatus = {
  encryption: { algorithm: string; configured: boolean };
  email_index: { algorithm: string; configured: boolean };
  hash: { algorithm: string; enabled: boolean };
  signature: {
    algorithm: string; standard: string; provider_available: boolean;
    private_key_configured: boolean; public_key_configured: boolean; enabled: boolean;
    key_id: string | null; public_key_bytes: number | null;
    available_signature_algorithms: string[];
  };
  ledger: { entries: number; latest_seq: number | null };
};

export type ChainVerification = {
  ok: boolean; checked: number; first_invalid_seq: number | null;
  checks: Record<string, boolean>;
};
