import { Injectable, ApplicationRef, signal } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { Subscription } from 'rxjs';

export interface MethodParameter {
  name: string;
  type: string;
  default: any;
}

export interface MethodDefinition {
  parameters: MethodParameter[];
}

export interface CommandResult {
  id: string;
  result: any;
  operation: string;
  status: 'pending' | 'success' | 'error';
  timestamp: number;
}

@Injectable({
  providedIn: 'root'
})
export class SocketService extends Socket {
  
  public messages = signal<string[]>([]);
  public clients = signal<string[]>([]);
  public methods = signal<Record<string, MethodDefinition>>({});
  public commandResults = signal<Record<string, CommandResult>>({});
  private activeClientId: string | null = null;
  private activeClientSubscriptions: Subscription[] = [];

  constructor(appRef: ApplicationRef) {
    super({ url: window.location.origin, options: {} }, appRef);
    
    this.fromEvent('methods.response').subscribe((data: any) => {
      console.log('Methods received:', data);
      this.methods.set(data);
    });

    this.fromEvent('clients.response').subscribe((data: any) => {
      console.log('Clients received:', data);
      
      const clients = Array.isArray(data) ? data : (data?.clients || []);
      
      this.clients.set(clients);
    });
  }

  fetchClients() {
    this.emit('clients.request');
  }

  fetchMethods() {
    this.emit('methods.request');
  }

  setActiveClient(clientId: string | null) {
    if (this.activeClientId === clientId) {
      return;
    }

    this.activeClientSubscriptions.forEach(subscription => subscription.unsubscribe());
    this.activeClientSubscriptions = [];
    this.activeClientId = clientId;

    if (!clientId) {
      this.commandResults.set({});
      return;
    }

    const resultsEvent = `results.response.${clientId}`;
    const pluginEvent = `plugin.response.${clientId}`;

    this.activeClientSubscriptions.push(
      this.fromEvent(resultsEvent).subscribe((data: any) => {
        const parsedResults = this.parseResultsPayload(data);
        const mappedResults: Record<string, CommandResult> = {};

        parsedResults.forEach((result: any, index: number) => {
          const id = result?.id;
          if (!id) {
            return;
          }

          mappedResults[id] = {
            id,
            result: result.data,
            operation: result.operation || this.commandResults()[id]?.operation || 'unknown',
            status: this.mapResultStatus(result.state),
            timestamp: this.commandResults()[id]?.timestamp || Date.now() + index
          };
        });

        this.commandResults.set(mappedResults);
      })
    );

    this.activeClientSubscriptions.push(
      this.fromEvent(pluginEvent).subscribe(() => {
        this.requestResults(clientId);
      })
    );

    this.requestResults(clientId);
  }

  requestResults(clientId: string) {
    this.emit('results.request', clientId);
  }

  runMethod(targetClient: string, operation: string, kwargs: any, callback?: (id: string) => void) {
    const payload = {
      client_id: targetClient,
      operation: operation,
      kwargs: kwargs
    };
    
    this.emit('plugin.run', payload, (id: string) => { 
      console.log(`Executed ID: ${id}`);
      this.commandResults.update(results => ({
        ...results,
        [id]: {
          id: id,
          result: null,
          operation,
          status: 'pending',
          timestamp: Date.now()
        }
      }));
      if (callback) callback(id);
    });
  }

  sendMessage(targetClient: string | null = null) {
    console.log('test', targetClient);
    const payload = {
      client_id: targetClient || 'test', 
      operation: 'website.render', 
      kwargs: { url: 'https://mnta.in/', bundle: true }
    };
    this.emit('plugin.run', payload, (id: string) => { console.log(`ID: ${id}`) })
  }

  private parseResultsPayload(data: any): any[] {
    if (Array.isArray(data)) {
      return data;
    }

    if (typeof data === 'string') {
      try {
        const parsed = JSON.parse(data);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }

    return [];
  }

  private mapResultStatus(state: string): 'pending' | 'success' | 'error' {
    if (state === 'error') {
      return 'error';
    }

    if (state === 'pending') {
      return 'pending';
    }

    return 'success';
  }
}
