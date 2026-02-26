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

export interface ClientInfo {
  id: string;
  connected: boolean;
  status: string;
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
  public clients = signal<ClientInfo[]>([]);
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

      this.clients.set(this.parseClientsPayload(data));
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

  removeClient(clientId: string) {
    this.emit('client.remove', clientId);
  }

  runMethod(targetClient: string, operation: string, kwargs: any, callback?: (id: string) => void) {
    const payload = {
      client_id: targetClient,
      operation: operation,
      kwargs: kwargs
    };
    
    this.emit('plugin.run', payload, (id: string) => { 
      console.log(`Executed ID: ${id}`);
      this.commandResults.update((results: Record<string, CommandResult>) => ({
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

  private parseClientsPayload(data: any): ClientInfo[] {
    if (Array.isArray(data)) {
      return data.map((client) => ({
        id: String(client),
        connected: true,
        status: 'connected'
      }));
    }

    const candidate = data?.clients && typeof data.clients === 'object' && !Array.isArray(data.clients)
      ? data.clients
      : data;

    if (!candidate || typeof candidate !== 'object') {
      return [];
    }

    return Object.entries(candidate).map(([id, value]) => {
      const status = this.extractClientStatus(value);
      return {
        id,
        connected: status === 'connected',
        status
      };
    });
  }

  private extractClientStatus(value: any): string {
    if (typeof value === 'string') {
      return this.normalizeStatus(value);
    }

    if (value instanceof Uint8Array) {
      return this.normalizeStatus(new TextDecoder().decode(value));
    }

    if (Array.isArray(value)) {
      return this.normalizeStatus(String.fromCharCode(...value));
    }

    if (value && typeof value === 'object') {
      if (value.type === 'Buffer' && Array.isArray(value.data)) {
        return this.normalizeStatus(String.fromCharCode(...value.data));
      }

      const nested = value.value ?? value.status ?? value.state ?? value.data;
      if (nested !== undefined) {
        return this.extractClientStatus(nested);
      }
    }

    return 'disconnected';
  }

  private normalizeStatus(rawStatus: string): string {
    const status = rawStatus.trim().toLowerCase();

    if (status === 'connected' || status === 'online' || status === 'true' || status === '1') {
      return 'connected';
    }

    if (status === 'disconnected' || status === 'offline' || status === 'false' || status === '0') {
      return 'disconnected';
    }

    return status || 'disconnected';
  }
}
