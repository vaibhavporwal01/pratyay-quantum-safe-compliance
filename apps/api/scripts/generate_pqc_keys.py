"""Generate an ML-DSA-65 key pair for the Pratyay ledger.

Run inside the PQC-enabled API image. Prints only Base64 values so they can be
stored in the deployment secret manager; never commit the output.
"""
import base64
import oqs

algorithm = "ML-DSA-65"
with oqs.Signature(algorithm) as signer:
    public = signer.generate_keypair()
    private = signer.export_secret_key()

print("LEDGER_MLDSA_PUBLIC_KEY=" + base64.b64encode(public).decode("ascii"))
print("LEDGER_MLDSA_PRIVATE_KEY=" + base64.b64encode(private).decode("ascii"))
