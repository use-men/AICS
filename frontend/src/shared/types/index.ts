export interface User {
  id: number;
  username: string;
  email: string;
  phone?: string;
  avatar?: string;
  nickname?: string;
  status: 'active' | 'inactive' | 'banned';
  roles: Role[];
  created_at: string;
  updated_at: string;
}

export interface Role {
  id: number;
  name: string;
  code: string;
  permissions: Permission[];
}

export interface Permission {
  id: number;
  name: string;
  code: string;
}

export interface Ticket {
  id: number;
  ticket_no: string;
  title: string;
  description: string;
  status: 'open' | 'in_progress' | 'pending' | 'resolved' | 'closed';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  category?: string;
  creator_id: number;
  assignee_id?: number;
  created_at: string;
  updated_at: string;
}

export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
  total?: number;
}
