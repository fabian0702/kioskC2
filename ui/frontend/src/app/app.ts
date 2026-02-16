import { Component, signal, inject, OnInit, computed, effect } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SocketService, MethodDefinition, MethodParameter } from './services/socket.service';
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
    const results = Object.values(this.commandResults()).sort((a,b) => b.timestamp - a.timestamp);
    console.log('Recomputed allCommandResults:', results);
    return results;
  });

  selectedClient = signal<string | null>(null);
  selectedMethod = signal<string | null>(null);
  
  // Stores current form values for method parameters
  methodArgs = signal<any>({});

  ngOnInit() {
    this.socketService.fetchClients();
    this.socketService.fetchMethods();
  }

  selectClient(client: string) {
    this.selectedClient.set(client);
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
      methodDef.parameters.forEach(param => {
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
}
