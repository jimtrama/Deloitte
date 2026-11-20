import { NgModule, provideZonelessChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { App } from './app';

@NgModule({
  declarations: [App],
  imports: [BrowserModule, FormsModule],
  providers: [provideHttpClient(), provideZonelessChangeDetection()],
  bootstrap: [App],
})
export class AppModule {}
