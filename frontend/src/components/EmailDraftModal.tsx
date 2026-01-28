import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { api } from "../api/client";
import type { Email } from "../api/client";
import "./EmailDraftModal.css";

interface EmailDraftModalProps {
  emailId: string;
  onClose: () => void;
  onUpdate?: () => void;
}

export function EmailDraftModal({
  emailId,
  onClose,
  onUpdate,
}: EmailDraftModalProps) {
  const [email, setEmail] = useState<Email | null>(null);
  const [persistedEmail, setPersistedEmail] = useState<Email | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [redrafting, setRedrafting] = useState(false);
  const [redraftPrompt, setRedraftPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadEmail = useCallback(async () => {
    try {
      const data = await api.getEmail(emailId);
      setEmail(data);
      setPersistedEmail(data);
    } catch (err) {
      console.error("Failed to load email draft:", err);
      setError("Failed to load email draft");
    } finally {
      setLoading(false);
    }
  }, [emailId]);

  useEffect(() => {
    loadEmail();
  }, [loadEmail]);

  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => {
      window.removeEventListener("keydown", handleEsc);
    };
  }, [onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const year = date.getFullYear().toString().slice(-2);
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${day}.${month}.${year} ${hours}:${minutes}h`;
  };

  const handleSave = async () => {
    if (!email) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateEmail(emailId, {
        subject: email.subject,
        body: email.body,
        recipient_email: email.recipient_email,
      });
      setPersistedEmail(email);
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error(err);
      setError("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleRedraft = async () => {
    if (!redraftPrompt.trim()) return;
    setRedrafting(true);
    setError(null);
    try {
      const updated = await api.redraftEmail(emailId, redraftPrompt);
      if (updated.subject === email?.subject && updated.body === email?.body) {
        setError("Ollama returned the same content. Try a different prompt.");
      } else {
        setEmail(updated);
        setPersistedEmail(updated);
        setRedraftPrompt("");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to re-draft email. Check if Ollama is running.");
    } finally {
      setRedrafting(false);
    }
  };

  const handleSend = async () => {
    if (!email) return;

    // Check if user has manual unsaved changes
    if (
      email.subject !== persistedEmail?.subject ||
      email.body !== persistedEmail?.body ||
      email.recipient_email !== persistedEmail?.recipient_email
    ) {
      setError("Please Save Draft before sending.");
      return;
    }

    // Check if lead has email (we need lead info for this, but if we have the draft,
    // the backend already checked it, but let's be safe if lead email was removed)
    setSending(true);
    setError(null);
    try {
      const result = await api.sendEmail(emailId);
      if (result.status === "success") {
        onClose();
        if (onUpdate) onUpdate();
      } else {
        setError(result.error || "Failed to send email");
      }
    } catch (err) {
      console.error(err);
      setError(
        "Failed to send email. Check if lead has a valid email address.",
      );
    } finally {
      setSending(false);
    }
  };

  if (loading)
    return createPortal(
      <div className="modal-overlay" onClick={handleOverlayClick}>
        <div className="spinner"></div>
      </div>,
      document.body,
    );

  return createPortal(
    <div className="modal-overlay" onClick={handleOverlayClick}>
      <div className="modal-content email-modal">
        <div className="modal-header">
          <div>
            <h2 className="text-gradient">Edit Email Draft</h2>
            {email?.generated_at && (
              <span className="timestamp-text">
                Created: {formatDate(email.generated_at)}
              </span>
            )}
          </div>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        {redrafting && (
          <div className="ollama-loader" style={{ margin: "1rem" }}>
            <div className="ollama-brain">🦙..🐏..🦙..🐏</div>
            <div className="ollama-text">Ollama is mhh mhh ing...</div>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}

        <div className="modal-body">
          <div className="form-group">
            <label>To:</label>
            <input
              type="email"
              value={email?.recipient_email || ""}
              onChange={(e) =>
                setEmail((prev) =>
                  prev ? { ...prev, recipient_email: e.target.value } : null,
                )
              }
              className="input-field"
              placeholder="recipient@example.com"
            />
          </div>

          <div className="form-group">
            <label>Subject</label>
            <input
              type="text"
              value={email?.subject || ""}
              onChange={(e) =>
                setEmail((prev) =>
                  prev ? { ...prev, subject: e.target.value } : null,
                )
              }
              className="input-field"
            />
          </div>

          <div className="form-group">
            <label>Message Body</label>
            <textarea
              value={email?.body || ""}
              onChange={(e) =>
                setEmail((prev) =>
                  prev ? { ...prev, body: e.target.value } : null,
                )
              }
              className="textarea-field"
              rows={10}
            />
          </div>

          <div className="redraft-container">
            <label>Refine Draft (Ollama)</label>
            <div className="redraft-input-group">
              <input
                type="text"
                value={redraftPrompt}
                onChange={(e) => setRedraftPrompt(e.target.value)}
                placeholder="e.g. Make it more formal, mention the discount..."
                className="input-field"
                onKeyPress={(e) => e.key === "Enter" && handleRedraft()}
              />
              <button
                className="btn btn-secondary btn-small"
                onClick={handleRedraft}
                disabled={redrafting || !redraftPrompt.trim()}
              >
                {redrafting ? "mhh mhh ing..." : "Re-Draft"}
              </button>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-outline"
            onClick={onClose}
            disabled={saving || sending || redrafting}
          >
            Cancel
          </button>
          <div className="footer-actions">
            <button
              className="btn btn-outline"
              onClick={handleSave}
              disabled={saving || sending || redrafting}
            >
              {saving ? "Saving..." : "Save Draft"}
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSend}
              disabled={saving || sending || redrafting}
            >
              {sending ? "Sending..." : "Send-Email"}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
