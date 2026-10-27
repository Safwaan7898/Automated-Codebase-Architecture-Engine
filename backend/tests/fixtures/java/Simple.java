package com.example.simple;

import java.util.List;
import java.util.ArrayList;

/**
 * A simple Java class used as a tree-sitter parser fixture.
 */
public class Simple {

    private String name;
    private int value;

    public Simple(String name, int value) {
        this.name = name;
        this.value = value;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getValue() {
        return value;
    }

    public List<String> buildItems(int count) {
        List<String> items = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            if (i % 2 == 0) {
                items.add(name + "_" + i);
            } else {
                items.add(String.valueOf(i));
            }
        }
        return items;
    }

    public static Simple of(String name) {
        return new Simple(name, 0);
    }
}
