import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { AskResponse, AskService, SearchMode } from './ask.service';

@Component({
  standalone: false,
  selector: 'app-root',
  styleUrl: './app.css',
  templateUrl: './app.html',
})
export class App {
  private readonly api = inject(AskService);
  question = '';
  searchMode: SearchMode = 'bm25';
  readonly searchModes: { value: SearchMode; label: string }[] = [
    { value: 'bm25', label: 'BM25' },
    { value: 'vector', label: 'Vector' },
    { value: 'hybrid', label: 'Hybrid' },
  ];
  readonly loading = signal(false);
  readonly result = signal<AskResponse | null>(null);
  readonly error = signal('');
  readonly examples = [
    'Ποια είναι η έδρα της εταιρείας;',
    'Ποιος είναι ο σκοπός της εταιρείας;',
    'Πώς φτιάχνω μακαρόνια;',
    'Ποτε ιδρύθηκε η εταιρεια ;'
  ];

  submit() {
    const question = this.question.trim();
    if (!question || this.loading()) return;

    this.loading.set(true);
    this.result.set(null);
    this.error.set('');

    this.api.ask(question, this.searchMode).subscribe({
      next: (response) => {
        this.result.set(response);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        let message = 'Could not get an answer. Check that FastAPI and Ollama are running.';
        if (error instanceof HttpErrorResponse && typeof error.error?.detail === 'string') {
          message = error.error.detail;
        } else if (error instanceof Error && error.name === 'TimeoutError') {
          message = 'The request took too long. Please try again.';
        }
        this.error.set(message);
        this.loading.set(false);
      },
    });
  }
}
