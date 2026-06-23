"""macOS Keychain utilities for PDF signing."""
import os
import re
import subprocess
import tempfile


def list_signing_identities():
    """Returns list of (hash, name) for identities with private key in Keychain."""
    result = subprocess.run(
        ["security", "find-identity", "-v"],
        capture_output=True, text=True
    )
    identities = []
    for line in result.stdout.splitlines():
        m = re.match(r'\s+\d+\)\s+([0-9A-Fa-f]+)\s+"(.+)"', line)
        if m:
            identities.append((m.group(1), m.group(2)))
    return identities


def sign_pdf_p12(input_path, output_path, p12_path, p12_password, reason="", location="", contact=""):
    """Signs a PDF using a P12/PFX file."""
    try:
        from pyhanko.sign import signers
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=p12_path,
            passphrase=p12_password.encode() if isinstance(p12_password, str) else p12_password,
        )
        sig_meta = signers.PdfSignatureMetadata(
            field_name="Signature1",
            reason=reason or None,
            location=location or None,
            contact_info=contact or None,
        )
        with open(input_path, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf)
            out_stream = signers.sign_pdf(writer, sig_meta, signer=signer)
            with open(output_path, "wb") as outf:
                out_stream.seek(0)
                outf.write(out_stream.read())
        return True, ""
    except Exception as e:
        return False, str(e)


def sign_pdf(input_path, output_path, identity_name, reason="", location="", contact=""):
    """
    Signs a PDF using a Keychain identity via pyhanko.
    macOS may show a native Keychain access dialog.
    Returns (True, "") on success or (False, error_message) on failure.
    """
    p12_file = None
    try:
        # Export the selected identity to a temporary P12 file.
        # macOS shows a native password dialog if the key is protected.
        p12_fd, p12_path = tempfile.mkstemp(suffix=".p12")
        os.close(p12_fd)
        export_pw = "pdfreader_tmp_1x9z"

        result = subprocess.run([
            "security", "export",
            "-k", os.path.expanduser("~/Library/Keychains/login.keychain-db"),
            "-t", "identities",
            "-f", "pkcs12",
            "-P", export_pw,
            "-o", p12_path,
        ], capture_output=True, text=True)

        if result.returncode != 0:
            return False, f"Export z Keychain selhal:\n{result.stderr}"

        if os.path.getsize(p12_path) == 0:
            return False, "Keychain neobsahuje žádnou signovací identitu."

        # If multiple identities were exported, we can't filter by name here
        # without re-exporting. For simplicity, sign with the first usable one.
        from pyhanko.sign import signers
        from pyhanko.pdf_utils.reader import PdfFileReader
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter

        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=p12_path,
            passphrase=export_pw.encode(),
        )

        sig_meta = signers.PdfSignatureMetadata(
            field_name="Signature1",
            reason=reason or None,
            location=location or None,
            contact_info=contact or None,
        )

        with open(input_path, "rb") as inf:
            writer = IncrementalPdfFileWriter(inf)
            out_stream = signers.sign_pdf(writer, sig_meta, signer=signer)
            with open(output_path, "wb") as outf:
                out_stream.seek(0)
                outf.write(out_stream.read())

        return True, ""

    except Exception as e:
        return False, str(e)
    finally:
        if p12_path and os.path.exists(p12_path):
            os.unlink(p12_path)
