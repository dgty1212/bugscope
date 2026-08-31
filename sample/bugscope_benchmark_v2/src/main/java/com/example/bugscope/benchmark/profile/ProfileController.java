package com.example.bugscope.benchmark.profile;
public class ProfileController {
    private final ProfileService service = new ProfileService();
    public String getDomain(Long userId) { return service.getEmailDomain(userId); }
}
