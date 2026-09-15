import React from "react";
import AudioRecorder from "../components/AudioRecorder";
import ClinicalSummary from "../components/ClinicalSummary";

export default function Transcription() {
  return (
    <div className="transcription-page">
      <AudioRecorder />
      <ClinicalSummary />
    </div>
  );
}
