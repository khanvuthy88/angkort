interface RootObject {
  id: number;
  name: string;
  birthday: string;
  avatar_128: string;
  avatar_256: string;
  avatar_512: string;
  avatar_1024: string;
  avatar_1920: string;
  department_id: IdNameObject;
  email: string;
  phone: string;
  gender: string;
  place_of_birth: string;
  emergency_contact: Emergencycontact;
  country_id: IdNameObject;
  identification_id: string;
  job_id: IdNameObject;
  job_title: string;
  marital: string;
  manager_id: IdNameObject;
  resume_line_ids: IdNameObject;
  skill_ids: Skillids;
}
interface Skillids {
  SkillObj: SkillObject[];
}
interface SkillObject {
  id: number;
  name: string;
  level_progress: number;
}
interface Resumelineids {
  Experience: Experience[];
  Education: Experience[];
}
interface Experience {
  id: number;
  name: string;
  date_start: string;
  date_end: string;
  description: string;
}
interface Emergencycontact {
  contact_name: string;
  contact_phone: string;
}
interface IdNameObject {
  id: number;
  name: string;
}