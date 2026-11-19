import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api } from "../api/client";
import { ReportView } from "./ReportPage";

export default function SharedReportPage() {
  const { token } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getSharedReport(token)
      .then((data) => setReport(data))
      .catch((err) => setError(err.message || "This shared report link is invalid or private."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-9 w-9 animate-spin rounded-full border-2 border-sand-300 border-t-burgundy" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <div className="journal-card p-8 space-y-4">
          <AlertCircle className="mx-auto h-10 w-10 text-verdict-unsupported" />
          <h1 className="font-display text-3xl font-bold text-plum-900">
            Shared report not found
          </h1>
          <p className="font-serif text-sm text-ink-muted">{error}</p>
          <Link to="/" className="btn-primary">
            Visit PaperProof
          </Link>
        </div>
      </div>
    );
  }

  return <ReportView report={report} readOnly={true} />;
}
