import { Component, signal, inject, OnInit, computed, effect } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SocketService, CommandResult, MethodParameter, ClientInfo } from './services/socket.service';
import { CommonModule, NgFor, NgIf, NgSwitch, NgSwitchCase, NgSwitchDefault, JsonPipe } from '@angular/common'; // added JsonPipe
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

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
  private sanitizer = inject(DomSanitizer);
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

  groupedMethods = computed(() => {
    const groups = new Map<string, string[]>();
    for (const key of this.methodKeys()) {
      const plugin = key.split('.')[0];
      if (!groups.has(plugin)) groups.set(plugin, []);
      groups.get(plugin)!.push(key);
    }
    return Array.from(groups.entries()).map(([plugin, keys]) => ({
      plugin,
      label: this.titleCase(plugin),
      keys
    }));
  });

  lastCommandId = signal<string | null>(null);
  lastCommandResult = computed(() => {
    const id = this.lastCommandId();
    if (id && this.commandResults()[id]) {
        return this.commandResults()[id];
    }
    return null;
  });

  sortKey = signal<'completed' | 'scheduled'>('completed');
  sortDir = signal<'desc' | 'asc'>('desc');

  allCommandResults = computed(() => {
    const results = Object.values(this.commandResults()) as CommandResult[];
    const key = this.sortKey();
    const dir = this.sortDir() === 'desc' ? -1 : 1;

    const sortValue = (cmd: CommandResult) =>
      key === 'completed' ? (cmd.completedAt ?? cmd.timestamp) : cmd.timestamp;

    results.sort((a, b) => (sortValue(a) - sortValue(b)) * dir);
    return results;
  });

  setSortKey(key: 'completed' | 'scheduled') {
    this.sortKey.set(key);
  }

  toggleSortDir() {
    this.sortDir.set(this.sortDir() === 'desc' ? 'asc' : 'desc');
  }

  selectedClient = signal<string | null>(null);
  selectedMethod = signal<string | null>(null);
  showDeleteConfirm = signal(false);
  pendingDeleteClientId = signal<string | null>(null);
  deleteStatus = signal<{ type: 'success' | 'error'; message: string } | null>(null);

  editingClientId = signal<string | null>(null);
  renameDraft = signal('');

  selectedClientInfo = computed(() => this.clients().find(c => c.id === this.selectedClient()) ?? null);

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

  startRename(client: ClientInfo, event: Event) {
    event.stopPropagation();
    this.editingClientId.set(client.id);
    this.renameDraft.set(client.alias || '');
  }

  commitRename(clientId: string) {
    if (this.editingClientId() !== clientId) {
      return;
    }
    this.socketService.renameClient(clientId, this.renameDraft());
    this.editingClientId.set(null);
  }

  cancelRename(event?: Event) {
    event?.stopPropagation();
    this.editingClientId.set(null);
  }

  formatLastSeen(ts: number | null | undefined): string {
    if (!ts) {
      return 'never';
    }
    const deltaSec = Math.floor((Date.now() - ts * 1000) / 1000);
    if (deltaSec < 5) return 'just now';
    if (deltaSec < 60) return `${deltaSec}s ago`;
    const min = Math.floor(deltaSec / 60);
    if (min < 60) return `${min}m ago`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}h ago`;
    return `${Math.floor(hr / 24)}d ago`;
  }

  private titleCase(s: string): string {
    return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  methodActionLabel(key: string): string {
    const action = key.split('.')[1];
    return action ? this.titleCase(action) : '';
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
           else if (param.type === 'Literal' && param.choices?.length) initialArgs[param.name] = param.choices[0];
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

  onFileChange(a: any, b: string, event: any) {
    let target: HTMLInputElement = event.target;
    a[b] = target && target.files && target.files[0];
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

  isAudio(result: any): boolean {
    return typeof result === 'string' && result.startsWith('data:audio/');
  }

  resultOutputType(cmd: CommandResult): 'image' | 'audio' | 'json' | 'code' | 'text' {
    const declared = this.methods()[cmd.operation]?.output;
    if (declared) {
      return declared;
    }
    if (this.isScreenshot(cmd.result)) return 'image';
    if (this.isAudio(cmd.result)) return 'audio';
    return 'text';
  }

  private escapeHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  highlightJson(value: any): SafeHtml {
    let text: string;
    if (typeof value === 'string') {
      text = value;
    } else {
      try {
        text = JSON.stringify(value, null, 2);
      } catch {
        text = String(value);
      }
    }

    const escaped = this.escapeHtml(text);
    const html = escaped.replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        let cls = 'json-number';
        if (/^"/.test(match)) {
          cls = /:$/.test(match) ? 'json-key' : 'json-string';
        } else if (match === 'true' || match === 'false') {
          cls = 'json-bool';
        } else if (match === 'null') {
          cls = 'json-null';
        }
        return `<span class="${cls}">${match}</span>`;
      }
    );

    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  deleteResult(id: string) {
    const client = this.selectedClient();
    if (client) this.socketService.deleteResult(client, id);
  }

  clearAllResults() {
    const client = this.selectedClient();
    if (client) this.socketService.clearResults(client);
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
