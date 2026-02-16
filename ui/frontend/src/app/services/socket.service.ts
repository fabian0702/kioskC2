import { Injectable, ApplicationRef, signal } from '@angular/core';
import { Socket } from 'ngx-socket-io';
import { map } from 'rxjs/operators';

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

  constructor(appRef: ApplicationRef) {
    super({ url: 'http://localhost:8001', options: {} }, appRef);
    
    this.fromEvent('plugin.response').subscribe((data: any) => {
      console.log('Message received (raw):', data);
      
      let parsedData = data;
      if (typeof data === 'string') {
        try {
            parsedData = JSON.parse(data);
        } catch (e) {
            console.error('Failed to parse message:', data);
            return;
        }
      }

      this.messages.update(msgs => [...msgs, parsedData.msg || JSON.stringify(parsedData)]);

      // Handle command result if ID is present
      if (parsedData.id) {
        console.log('Updating command result for ID:', parsedData.id); 
        this.commandResults.update(results => {
          const newResults = {
            ...results,
            [parsedData.id]: {
              ...(results[parsedData.id] || {}),
              id: parsedData.id,
              result: parsedData.data || parsedData.result || parsedData.msg,
              status: 'success',
              // careful not to overwrite timestamp if we want to keep order, 
              // or overwrite if we want to bump to top. Current sort is desc timestamp.
              timestamp: results[parsedData.id]?.timestamp || Date.now() 
            }
          };
          console.log('New command results state:', newResults);
          return newResults;
        });
      } else {
         console.warn('Received plugin.response without ID:', parsedData);
      }
    });

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
}
