import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';

export interface Source {
  document: string;
  section: string;
  page: number;
}

export interface AskResponse {
  answer: string;
  sources: Source[];
}

@Injectable({ providedIn: 'root' })
export class AskService {
  private readonly http = inject(HttpClient);

  ask(question: string) {
    return this.http.post<AskResponse>('/ask', { question }).pipe(timeout(130_000));
  }
}
