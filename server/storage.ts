import { type User, type InsertUser, type InsertAnalysis, type AnalysisHistory as AnalysisHistoryType } from "@shared/schema";
import { randomUUID } from "crypto";

export interface IStorage {
  getUser(id: string): Promise<User | undefined>;
  getUserByUsername(username: string): Promise<User | undefined>;
  createUser(user: InsertUser): Promise<User>;
  saveAnalysis(analysis: InsertAnalysis): Promise<AnalysisHistoryType>;
  getAnalysisHistory(limit?: number): Promise<AnalysisHistoryType[]>;
}

export class MemStorage implements IStorage {
  private users: Map<string, User>;
  private analyses: AnalysisHistoryType[];
  private analysisIdCounter: number;

  constructor() {
    this.users = new Map();
    this.analyses = [];
    this.analysisIdCounter = 1;
  }

  async getUser(id: string): Promise<User | undefined> {
    return this.users.get(id);
  }

  async getUserByUsername(username: string): Promise<User | undefined> {
    return Array.from(this.users.values()).find(
      (user) => user.username === username,
    );
  }

  async createUser(insertUser: InsertUser): Promise<User> {
    const id = randomUUID();
    const user: User = { ...insertUser, id };
    this.users.set(id, user);
    return user;
  }

  async saveAnalysis(analysis: InsertAnalysis): Promise<AnalysisHistoryType> {
    const newAnalysis: AnalysisHistoryType = {
      ...analysis,
      id: this.analysisIdCounter++,
      createdAt: new Date(),
    };
    this.analyses.unshift(newAnalysis);
    if (this.analyses.length > 100) {
      this.analyses = this.analyses.slice(0, 100);
    }
    return newAnalysis;
  }

  async getAnalysisHistory(limit: number = 20): Promise<AnalysisHistoryType[]> {
    return this.analyses.slice(0, limit);
  }
}

export const storage = new MemStorage();
