import { useState, useEffect, useCallback } from "react";
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
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadEmail = useCallback(async () => {
    try {
      const data = await api.getEmail(emailId);
      setEmail(data);
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

  const handleSave = async () => {
    if (!email) return;
    setSaving(true);
    try {
      await api.updateEmail(emailId, {
        subject: email.subject,
        body: email.body,
      });
      if (onUpdate) onUpdate();
    } catch (err) {
      console.error(err);
      setError("Failed to save changes");
    } finally {
      setSaving(false);
    }
  };

  const handleSend = async () => {
    if (!email) return;
    setSending(true);
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
      setError("Failed to send email");
    } finally {
      setSending(false);
    }
  };

  if (loading)
    return (
      <div className="modal-overlay">
        <div className="spinner"></div>
      </div>
    );

  return (
    <div className="modal-overlay">
      <div className="modal-content email-modal">
        <div className="modal-header">
          <h2 className="text-gradient">Edit Email Draft</h2>
          <button className="close-btn" onClick={onClose}>
            &times;
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="modal-body">
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
              rows={12}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-outline"
            onClick={onClose}
            disabled={saving || sending}
          >
            Cancel
          </button>
          <div className="footer-actions">
            <button
              className="btn btn-outline"
              onClick={handleSave}
              disabled={saving || sending}
            >
              {saving ? "Saving..." : "Save Draft"}
            </button>
            <button
              className="btn"
              onClick={handleSend}
              disabled={saving || sending}
            >
              {sending ? "Sending..." : "Send Now"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
