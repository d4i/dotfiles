#!/usr/bin/env python


from __future__ import with_statement
import re
import yaml
from fabric.api import sudo, run, settings, env, task
from fabric.contrib.files import exists

if len(env.hosts) == 0:
    env.hosts = ['localhost']
env.use_ssh_config = True


@task
def setup_system(yml='pkg/system.yml'):
    os_type = run("echo $OSTYPE")
    with settings(warn_only=True):
        if re.match(r'^linux', os_type):
            if sudo("cat /etc/redhat-release").succeeded:
                setup_with_dnf()
            elif sudo("cat /etc/lsb-release").succeeded:
                setup_with_apt()
        elif re.match(r'^darwin', os_type):
            setup_with_brew()


@task
def setup_with_dnf(yml='config/dnf.yml'):
    with open(yml) as f:
        pkg = yaml.load(f)
    if sudo("dnf --version").succeeded:
        sudo("dnf -y upgrade")
        if sudo("dnf -y --allowerasing install %s" % ' '.join(pkg['dnf'])).failed:
            map(lambda p: sudo("dnf -y install %s" % p), pkg['dnf'])
        sudo("dnf clean all")
    elif sudo("yum --version").succeeded:
        sudo("yum -y upgrade")
        if sudo("yum -y --skip-broken install %s" % ' '.join(pkg['dnf'])).failed:
            map(lambda p: sudo("yum -y install %s" % p), pkg['dnf'])
        sudo("yum clean all")


@task
def setup_with_apt(yml='config/apt.yml'):
    with open(yml) as f:
        pkg = yaml.load(f)
    if sudo("apt-get --version").succeeded:
        sudo("apt-get -y upgrade && apt-get -y update")
        if sudo("apt-get -y install %s" % ' '.join(pkg['apt'])).failed:
            map(lambda p: sudo("apt-get -y install %s" % p), pkg['apt'])
        sudo("apt-get clean")


@task
def setup_with_brew(yml='config/brew.yml'):
    with open(yml) as f:
        pkg = yaml.load(f)
    if run("brew --version").failed:
        run("/usr/bin/ruby -e $(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)")
    else:
        run("brew update && brew upgrade --all")
    map(lambda p: run("brew install %s" % p), pkg['brew'])
    run("brew cleanup")


def install_lang(l, pkg):
    ver = run("%s install --list | grep -e '^  \+%d\.[0-9]\+\.[0-9]\+$' | cut -f 3 -d ' ' | tail -1" % (l['e'], l['v']))
    if run("%s versions | grep -e '\\s%s' || %s install %s" % (l['e'], ver, l['e'], ver)).succeeded:
        run("%s global %s" % (l['e'], ver))
        if re.match(r'pyenv$', l['e']):
            run("%s --version" % pkg['cmd'])
            map(lambda p: run("%s --no-cache-dir install -U %s" % (pkg['cmd'], p)),
                set(run("%s list | cut -f 1 -d ' '" % pkg['cmd']).split() + pkg['pip']).difference({'pip'}))
        elif re.match(r'rbenv$', l['e']):
            run("%s --version" % pkg['cmd'])
            run("%s update" % pkg['cmd'])
            map(lambda p: run("%s install --no-document %s" % (pkg['cmd'], p)), pkg['gem'])


@task
def setup_py_env(yml='config/pip.yml'):
    if exists('~/.pyenv/.git'):
        run("cd ~/.pyenv && git pull")
        pyenv = '~/.pyenv/bin/pyenv'
    elif exists('~/.pyenv'):
        pyenv = 'pyenv'
    else:
        run("git clone https://github.com/yyuu/pyenv.git ~/.pyenv")
        pyenv = '~/.pyenv/bin/pyenv'
    with open(yml) as f:
        pkg = yaml.load(f)
    with settings(warn_only=True):
        install_lang({'e': pyenv, 'v': 2}, pkg)
        install_lang({'e': pyenv, 'v': 3}, pkg)


@task
def setup_rb_env(yml='config/gem.yml'):
    if exists('~/.rbenv/.git'):
        run("cd ~/.rbenv && git pull")
        run("cd ~/.rbenv/plugins/ruby-build && git pull")
        rbenv = '~/.rbenv/bin/rbenv'
    elif exists('~/.rbenv'):
        rbenv = 'rbenv'
    else:
        run("git clone https://github.com/sstephenson/rbenv.git ~/.rbenv")
        run("git clone https://github.com/sstephenson/ruby-build.git ~/.rbenv/plugins/ruby-build")
        rbenv = '~/.rbenv/bin/rbenv'
    with open(yml) as f:
        pkg = yaml.load(f)
    with settings(warn_only=True):
        install_lang({'e': rbenv, 'v': 2}, pkg)


@task
def setup_go_env(yml='config/go.yml'):
    with open(yml) as f:
        pkg = yaml.load(f)
    with settings(warn_only=True):
        if run("go version").succeeded:
            gopath = '~/.go'
            go = 'export GOPATH=' + gopath + ' && go'
            if not exists(gopath):
                run("mkdir -p %s" % gopath)
            else:
                run("%s get -u all" % go)
            map(lambda p: run("%s get -v %s" % (go, p)), pkg['go'])


@task
def setup_r_env(script='script/install_r_libs.R'):
    with settings(warn_only=True):
        if run("R --version").succeeded:
            r_libs = '~/.R/library'
            if not exists(r_libs):
                run("mkdir -p %s" % r_libs)
            with open(script) as f:
                src = f.read()
            run("export R_LIBS=%s && echo '%s' | R -q --vanilla" % (r_libs, re.sub(r'([^\\])\'', r'\1"', src)))


@task
def setup_zsh_env():
    dot_files = ('.zshrc', '.vimrc')
    if not exists('~/fabkit'):
        run("git clone https://github.com/dceoy/fabkit.git ~/fabkit")
    else:
        run("cd ~/fabkit && git pull")
    map(lambda f: run("[[ -f ~/%s ]] || ln -s ~/fabkit/dotfile/%s ~/%s" % (f, 'd' + f, f)), dot_files)

    if not re.match(r'.*\/zsh$', run("echo $SHELL")):
        run("chsh -s $(grep -e '\/zsh$' /etc/shells | tail -1) %s" % env.user)


@task
def setup_vim_env():
    if not exists('~/.vim/bundle/vimproc.vim'):
        run("mkdir -p ~/.vim/bundle")
        run("git clone https://github.com/Shougo/vimproc.vim.git ~/.vim/bundle/vimproc.vim")
        run("cd ~/.vim/bundle/vimproc.vim && make")
    if not exists('~/.vim/bundle/neobundle.vim'):
        run("git clone https://github.com/Shougo/neobundle.vim.git ~/.vim/bundle/neobundle.vim")
    run("~/.vim/bundle/neobundle.vim/bin/neoinstall")


if __name__ == '__main__':
    print("Usage: fab [options] <command>[:arg1,arg2=val2,host=foo,hosts='h1;h2',...] ...")
