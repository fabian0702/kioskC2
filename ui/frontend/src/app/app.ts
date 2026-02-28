import { Component, signal, inject, OnInit, computed, effect } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SocketService, CommandResult, MethodParameter } from './services/socket.service';
import { CommonModule, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, JsonPipe } from '@angular/common'; // added JsonPipe
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule, NgFor, NgIf, FormsModule, NgSwitch, NgSwitchCase, NgSwitchDefault, JsonPipe],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  protected readonly title = signal('kiosk-frontend');
  protected socketService = inject(SocketService);
  clientJoinUrl = `${window.location.protocol}//clients.${window.location.host}/`;
  
  messages = this.socketService.messages;
  clients = this.socketService.clients;
  methods = this.socketService.methods;
  commandResults = this.socketService.commandResults; // ensure direct signal reference
  
  constructor() {
    effect(() => {
        console.log('Component sees command results update:', this.commandResults());
    });
  }
  
  methodKeys = computed(() => Object.keys(this.methods()));

  lastCommandId = signal<string | null>(null);
  lastCommandResult = computed(() => {
    const id = this.lastCommandId();
    if (id && this.commandResults()[id]) {
        return this.commandResults()[id];
    }
    return null;
  });

  allCommandResults = computed(() => {
    const results = Object.values(this.commandResults()) as CommandResult[];
    results.sort((a, b) => b.timestamp - a.timestamp);
    console.log('Recomputed allCommandResults:', results);
    return results;
  });

  selectedClient = signal<string | null>(null);
  selectedMethod = signal<string | null>(null);
  showDeleteConfirm = signal(false);
  pendingDeleteClientId = signal<string | null>(null);
  deleteStatus = signal<{ type: 'success' | 'error'; message: string } | null>(null);
  
  // Stores current form values for method parameters
  methodArgs = signal<any>({});

  ngOnInit() {
    this.socketService.fetchClients();
    this.socketService.fetchMethods();
  }

  selectClient(client: string) {
    this.selectedClient.set(client);
    this.socketService.setActiveClient(client);
  }

  selectMethod(methodName: string) {
    if (!methodName) { 
        this.selectedMethod.set(null); 
        return; 
    }
    this.selectedMethod.set(methodName);
    
    // Initialize default values
    const methodDef = this.methods()[methodName];
    const initialArgs: any = {};
    if (methodDef && methodDef.parameters) {
      methodDef.parameters.forEach((param: MethodParameter) => {
        // Use default if available, else sensible type default
        if (param.default !== null && param.default !== undefined) {
           initialArgs[param.name] = param.default;
        } else {
           if (param.type === 'bool') initialArgs[param.name] = false;
           else if (param.type === 'int') initialArgs[param.name] = 0;
           else initialArgs[param.name] = '';
        }
      });
    }
    this.methodArgs.set(initialArgs);
  }

  runSelectedMethod() {
    const client = this.selectedClient();
    const method = this.selectedMethod();
    const args = this.methodArgs();

    if (client && method) {
      this.lastCommandId.set(null); // Reset UI display
      this.socketService.runMethod(client, method, args, (id: string) => {
        this.lastCommandId.set(id);
      });
    }
  }

  openDeleteConfirm(clientId: string, event: Event) {
    event.stopPropagation();
    this.pendingDeleteClientId.set(clientId);
    this.showDeleteConfirm.set(true);
  }

  cancelDelete() {
    this.showDeleteConfirm.set(false);
    this.pendingDeleteClientId.set(null);
  }

  isScreenshot(result: any): boolean {
    return typeof result === 'string' && result.startsWith('data:image/');
  }

  confirmDelete() {
    const clientId = this.pendingDeleteClientId();
    if (!clientId) {
      this.cancelDelete();
      return;
    }

    try {
      this.socketService.removeClient(clientId);

      if (this.selectedClient() === clientId) {
        this.selectedClient.set(null);
        this.selectedMethod.set(null);
        this.methodArgs.set({});
        this.socketService.setActiveClient(null);
      }

      this.deleteStatus.set({
        type: 'success',
        message: `Delete request sent for ${clientId}`
      });
    } catch (error) {
      console.error('Error removing client:', error);
      this.deleteStatus.set({
        type: 'error',
        message: `Failed to delete ${clientId}`
      });
    } finally {
      this.cancelDelete();
    }
  }
}
