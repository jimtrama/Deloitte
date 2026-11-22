import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { timeout } from 'rxjs';

export type SearchMode = 'bm25' | 'vector' | 'hybrid';

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

  ask(question: string, searchMode: SearchMode = 'bm25') {
    return this.http.post<AskResponse>('/ask', {
      question,
      search_mode: searchMode,
    }).pipe(timeout(130_000));
  }
}
